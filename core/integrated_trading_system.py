import threading
import time
import signal
import logging
import traceback
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Set
import numpy as np

from api.account_manager import init_account_manager
from analytics import trade_summary
from utils.notifier import notifier
from strategies.closing_price_trader import closing_price_stock_filter
from strategies.swing_screener import get_swing_candidates, is_etf_like
from strategies.news_handler import on_news_event
from data.data_logger import data_logger
from data.event_logger import event_logger
from web_socket.web_socket_manager import KISWebSocketClient
from web_socket.market_cache import init_market_cache    
from core.config import config
from core.position_manager import RealPositionManager
from utils.balance_manager import BalanceManager
from utils.news_fetcher import news_fetcher

logger = logging.getLogger(__name__)

class IntegratedTradingSystem:
    """종가 매매 및 익일 시초가 매도 전략 기반 통합 거래 시스템"""
    
    def __init__(self, system_config: Dict):
        self.config = system_config
        self.shutdown_event = threading.Event()
        self.account_manager = None
        self.position_manager = RealPositionManager()
        self.balance_manager = BalanceManager()
        self.ws_manager: KISWebSocketClient = None
        self.subscribed_codes: Set[str] = set()
        self.beginning_total_assets = 0

        self.closing_price_candidates: List[Dict] = []
        self.swing_candidates: Dict[str, Dict] = {}
        self.last_news_timestamp: Dict[str, datetime] = {}
        self.sell_worker_done_today = False
        self.buy_worker_done_today = False
        
        self.positions_to_sell: Dict[str, Dict] = {}
        self.sell_peaks: Dict[str, float] = {}
        self.sell_open_prices: Dict[str, float] = {}

        signal.signal(signal.SIGINT, self._signal_handler)
        self.market_cache = None
        logger.info("[SYSTEM] 종가 매매 전략 시스템으로 초기화")

    def _normalize_code(self, code: str) -> str:
        return f"A{str(code).lstrip('A').zfill(6)}"

    def initialize(self) -> bool:
        try:
            logger.info("[SYSTEM] 시스템 초기화 시작")
            api_config = self.config.get('api', {})
            self.account_manager = init_account_manager(
                api_config['app_key'], api_config['app_secret'], api_config['account_no']
            )
            if not (self.account_manager and self.account_manager.api.access_token):
                raise Exception("API 계정 인증 실패")
            logger.info("[SYSTEM] API 계정 인증 완료")

            self.market_cache = init_market_cache(self.config, self.position_manager, self.account_manager)
            
            self.beginning_total_assets = self.account_manager.get_total_assets()
            if self.beginning_total_assets == 0:
                logger.error("[SYSTEM] 시작 총자산 조회 실패. 시스템을 시작할 수 없습니다.")
                return False

            cash_balance = self.account_manager.get_simple_balance()
            self.balance_manager.set_balance(cash_balance)
            trade_summary.set_starting_balance(self.beginning_total_assets)
            logger.info(f"[SYSTEM] 시작 총자산: {self.beginning_total_assets:,}원, 현금: {cash_balance:,}원")

            current_positions = self.account_manager.get_current_positions()
            codes_to_subscribe = set()
            if current_positions:
                logger.info(f"[SYSTEM] {len(current_positions)}개 보유 종목 발견")
                for pos in current_positions:
                    code = self._normalize_code(pos.get('pdno'))
                    self.position_manager.add_position(code, int(pos.get('hldg_qty')), float(pos.get('pchs_avg_pric')), pos.get('prdt_name'))
                    codes_to_subscribe.add(code)
                logger.info(f"[SYSTEM] 보유 종목 포지션 복원 완료: {list(codes_to_subscribe)}")
            
            approval_key = self.account_manager.api.get_approval_key()
            if not approval_key: raise Exception("웹소켓 승인 키 발급 실패")

            self.ws_manager = KISWebSocketClient(config=self.config, account_manager=self.account_manager, approval_key=approval_key, codes=codes_to_subscribe, market_cache=self.market_cache)
            self.subscribed_codes.update(codes_to_subscribe)
            logger.info(f"[SYSTEM] 시스템 초기화 완료. 보유 종목 {len(self.subscribed_codes)}개 구독 준비 완료.")
            return True
            
        except Exception as e:
            logger.error(f"[SYSTEM] 초기화 실패: {e}", exc_info=True)
            return False

    def run(self):
        if not self.initialize():
            self.shutdown()
            return False

        if not self._wait_and_connect_ws():
            logger.error("[SYSTEM] 웹소켓 연결 실패. 시스템 종료.")
            self.shutdown()
            return False

        logger.info("[SYSTEM] 종가 매매 시스템 실행 시작")
        self._start_workers()
        
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("[SYSTEM] 사용자 중단 요청")
        finally:
            self.shutdown()
        return True

    def _start_workers(self):
        threading.Thread(target=self._opening_sell_worker, daemon=True).start()
        threading.Thread(target=self._closing_price_screening_worker, daemon=True).start()
        threading.Thread(target=self._closing_price_buy_worker, daemon=True).start()
        threading.Thread(target=self._news_event_worker, daemon=True).start()
        threading.Thread(target=self._daily_reset_worker, daemon=True).start()
        logger.info("[WORKER] 모든 워커 시작 완료")

    def _is_sell_time(self, now: datetime) -> bool:
        return dt_time(9, 0) <= now.time() < dt_time(15, 20)

    def _is_screening_time(self, now: datetime) -> bool:
        return dt_time(9, 30) <= now.time() < dt_time(15, 20)

    def _is_buy_time(self, now: datetime) -> bool:
        return now.time() >= dt_time(15, 18) and now.time() < dt_time(15, 29)

    def _daily_reset_worker(self):
        while not self.shutdown_event.is_set():
            now = datetime.now()
            if now.time() >= dt_time(0, 0) and now.time() < dt_time(0, 1):
                if self.sell_worker_done_today or self.buy_worker_done_today:
                    logger.info("[SYSTEM] 자정 리셋: 일일 작업 플래그를 초기화합니다.")
                    self.sell_worker_done_today = False
                    self.buy_worker_done_today = False
                    self.last_news_timestamp = {}
            time.sleep(60)

    def _opening_sell_worker(self):
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_sell_time(now) and not self.sell_worker_done_today:
                    if not self.positions_to_sell and self.position_manager.positions:
                        self.positions_to_sell = dict(self.position_manager.positions.items())
                        logger.info(f"[SELL_WORKER] init: positions_to_sell={list(self.positions_to_sell.keys())}")
                        
                        for code, position in self.positions_to_sell.items():
                            open_price = 0
                            for _ in range(10):
                                quote = self.market_cache.get_quote_full(code)
                                if quote and quote.get('price') > 0 and now.time() >= dt_time(9,0):
                                    open_price = quote.get('price')
                                    break
                                time.sleep(1)
                            
                            if open_price > 0:
                                self.sell_open_prices[code] = open_price
                                self.sell_peaks[code] = max(position.get('price', open_price), open_price)
                                logger.info(f"[SELL_WORKER] {position['name']} 시가 설정: {open_price}")
                            else: 
                                self.sell_open_prices[code] = position.get('price', 0)
                                self.sell_peaks[code] = position.get('price', 0)
                                logger.warning(f"[SELL_WORKER] {position['name']} 시가 조회 실패. 매수 평균가를 사용합니다.")

                    if not self.positions_to_sell:
                        if not self.sell_worker_done_today:
                            logger.info("[SELL_WORKER] 모든 보유 종목 매도 완료. 익일 매도 작업을 종료합니다.")
                            self.sell_worker_done_today = True
                        continue

                    positions_to_check = list(self.positions_to_sell.keys())
                    for code in positions_to_check:
                        quote = self.market_cache.get_quote_full(code)
                        if quote and quote.get('price') > 0:
                            self._check_sell_conditions(code, quote.get('price'))
                
                if now.time() >= dt_time(15, 20) and not self.sell_worker_done_today:
                    logger.info("[SELL_WORKER] 장 마감 시간 도달, 매도 작업을 종료합니다.")
                    if self.positions_to_sell:
                        logger.info(f"[SELL_WORKER] 미청산 종목: {list(self.positions_to_sell.keys())}")
                    self.sell_worker_done_today = True

                time.sleep(2)
            except Exception as e:
                logger.error(f"[SELL_WORKER] 오류: {e}", exc_info=True)
                time.sleep(60)

    def _check_sell_conditions(self, code: str, current_price: float):
        position = self.positions_to_sell.get(code)
        if not position: return

        avg_price = position.get('price', 0)
        if avg_price == 0: return

        now = datetime.now()
        logger.debug(f"[SELL_TICK] {code} cur={current_price} avg={avg_price} open={self.sell_open_prices.get(code)} peak={self.sell_peaks.get(code)}")

        self.sell_peaks[code] = max(self.sell_peaks.get(code, 0), current_price)
        peak_price = self.sell_peaks[code]

        profit = (current_price / avg_price) - 1
        trading_config = self.config.get('trading', {})

        early_session_end_time_str = trading_config.get("early_session_end_time", "09:05")
        early_session_end_time = dt_time.fromisoformat(early_session_end_time_str)
        if now.time() < early_session_end_time:
            early_hard_stop_ratio = trading_config.get('early_session_hard_stop_ratio', 0.98)
            if current_price <= avg_price * early_hard_stop_ratio:
                self._execute_sell(code, f"Early Hard Stop ({(current_price/avg_price-1):.2%})")
                return

        hard_stop_ratio = trading_config.get('hard_stop_from_avg_ratio', 0.97)
        if current_price <= avg_price * hard_stop_ratio:
            self._execute_sell(code, f"Hard Stop ({(current_price/avg_price-1):.2%})")
            return
        
        min_profit_pct = trading_config.get('min_profit_pct_sell', 0.001)
        trail_drop_pct = trading_config.get('trail_drop_pct_sell', 0.004)
        if profit >= min_profit_pct and (peak_price / current_price - 1) >= trail_drop_pct:
            self._execute_sell(code, f"Trailing Stop (수익률: {profit:.2%})")
            return

        open_price = self.sell_open_prices.get(code, 0)
        if open_price > 0:
            open_fail_drop_ratio = trading_config.get('open_fail_drop_ratio', 0.99)
            if profit < min_profit_pct and current_price < (open_price * open_fail_drop_ratio):
                self._execute_sell(code, f"Open Fail Stop (시가대비: {(current_price/open_price-1):.2%})")
                return

    def _execute_sell(self, code: str, reason: str):
        if code not in self.positions_to_sell: return

        pos = self.positions_to_sell[code]
        req_shares = int(pos['shares'])
        logger.info(f"[SELL] 매도 조건 충족: {pos['name']} ({code}) - 사유: {reason}, 요청수량: {req_shares}")

        # 실시간 보유/가용수량 조회
        try:
            holdings = self.account_manager.get_current_positions()
            avail = 0
            for h in holdings:
                if self._normalize_code(h.get('pdno')) == code:
                    avail = int(h.get('ord_psbl_qty') or h.get('hldg_qty') or 0)
                    logger.info(f"[SELL] {pos['name']} 실시간 가용수량 확인: {avail}주")
                    break
        except Exception as e:
            logger.error(f"[SELL] {pos['name']} 가용수량 조회 실패: {e}", exc_info=True)
            avail = 0 # 실패 시 매도 보류

        sell_qty = max(0, min(req_shares, avail))
        if sell_qty <= 0:
            logger.warning(f"[SELL] {pos['name']} ({code}) 가용수량 0 (요청: {req_shares}) → 매도 스킵")
            # 가용수량이 0이면 더 이상 매도 시도를 하지 않도록 목록에서 제거
            del self.positions_to_sell[code]
            return

        if sell_qty < req_shares:
            logger.warning(f"[SELL] {pos['name']} ({code}) 요청수량({req_shares})보다 가용수량({avail})이 적어 {sell_qty}주만 매도합니다.")

        result = self.account_manager.place_sell_order_market(code, sell_qty)
        if result and result.get('success'):
            current_price = self.market_cache.get_quote(code) or pos.get('price', 0)
            self.position_manager.close_position(
                code=code, quantity=sell_qty, price=current_price, reason=reason, name=pos['name']
            )
            logger.info(f"[SELL] 시장가 매도 주문 완료 및 포지션 종료: {pos['name']} ({code}) {sell_qty}주")
            del self.positions_to_sell[code]
        else:
            # 주문 실패 시, 상세 오류 메시지 로깅
            error_msg = result.get('error', '알 수 없는 오류')
            full_response = result.get('full_response', {})
            logger.error(f"[SELL] 매도 주문 실패: {pos['name']} ({code}), 사유: {error_msg}, 응답: {full_response}")

    def _normalize_stock(self, rec: Dict) -> Dict:
        """KIS API 응답을 내부 표준 형식으로 정규화합니다."""
        name = rec.get("name") or rec.get("stock_name") or rec.get("hts_kor_isnm") or ""
        code = rec.get("code") or rec.get("symbol") or rec.get("mksc_shrn_iscd") or rec.get("srtn_cd") or ""
        rank = rec.get("volume_rank") or rec.get("rank") or rec.get("stck_ranking") or None
        return {"name": name, "code": code, "volume_rank": rank, **rec}



    def _closing_price_screening_worker(self):
        """장중 후보군 스크리닝 (09:30 ~ 15:20)"""
        
        def _append_news_line(lines, name):
            if not news_fetcher:
                return
            try:
                n = news_fetcher.search_latest_news(name)
                if n and n.get("title"):
                    ts = n.get("timestamp", "")
                    lines.append(f"    · 📰 {ts} {n['title']}  {n['link']}")
            except Exception:
                pass

        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_screening_time(now):
                    logger.info("[SCREENER] 종가/스윙 후보군 스크리닝 시작...")
                    
                    raw_volume_stocks = self.account_manager.get_volume_ranking(count=100)
                    volume_stocks = [self._normalize_stock(r) for r in raw_volume_stocks]

                    swing_candidates_list = get_swing_candidates(volume_stocks, self.config, self.market_cache)
                    self.swing_candidates = {s['code']: s for s in swing_candidates_list}

                    self.closing_price_candidates = closing_price_stock_filter(
                        self.market_cache, volume_stocks, self.account_manager.api
                    )

                    if not self.closing_price_candidates and volume_stocks:
                        logger.warning("[SCREENER] 종가매매 필터링 후보가 없어 거래량 상위 종목으로 Fallback합니다.")
                        trading_config = self.config.get('trading', {})
                        exclude_keywords = trading_config.get('exclude_keywords', [])
                        fallback_candidates = []
                        for stock in volume_stocks:
                            stock_name = stock.get('name', '')
                            if any(keyword.upper() in stock_name.upper() for keyword in exclude_keywords):
                                continue
                            fallback_candidates.append({
                                'code': stock.get('code'), 'name': stock_name, 'turnover': stock.get('turnover', 0),
                                'total_score': 0.0, 'scores': {}, 'reason': 'fallback_volume'
                            })
                            if len(fallback_candidates) >= 5: break
                        self.closing_price_candidates = fallback_candidates

                    logger.info(f"[SCREENER] 종가매매 후보군 업데이트 완료: {len(self.closing_price_candidates)}개")
                    logger.info(f"[SCREENER] 스윙 후보군 업데이트 완료: {len(self.swing_candidates)}개")

                    if self.closing_price_candidates or self.swing_candidates:
                        top_n = 5
                        message_lines = ["*🔔 종가/스윙 후보 업데이트*"]
                        
                        # 종가 후보 생성
                        message_lines.append("\n*📈 종가매매 후보*")
                        if self.closing_price_candidates:
                            for i, stock in enumerate(self.closing_price_candidates[:top_n]):
                                score_display = f"점수: {stock.get('total_score', 0):.1f}"
                                line = f"{i+1}. {stock['name']} ({stock['code']}) - {score_display}"
                                message_lines.append(line)
                                _append_news_line(message_lines, stock['name'])
                        else:
                            message_lines.append("- 후보 없음")

                        # 스윙 후보 생성
                        message_lines.append("\n*🪝 스윙 후보 (모니터링)*")
                        if self.swing_candidates:
                            for i, stock in enumerate(list(self.swing_candidates.values())[:top_n]):
                                line = f"{i+1}. {stock['name']} ({stock['code']}) (거래량순위: {stock.get('volume_rank', 'N/A')})"
                                message_lines.append(line)
                                _append_news_line(message_lines, stock['name'])
                        else:
                            message_lines.append("- 후보 없음")

                        full_message = "\n".join(message_lines)
                        logger.info(full_message)
                        notifier.send_message(full_message)
                    
                    closing_codes = {self._normalize_code(c['code']) for c in self.closing_price_candidates}
                    swing_codes = {self._normalize_code(c['code']) for c in self.swing_candidates.values()}
                    self._update_subscriptions(closing_codes.union(swing_codes))

                time.sleep(300)
            except Exception as e:
                logger.error(f"[SCREENER] 오류: {e}", exc_info=True)
                time.sleep(300)

    def _news_event_worker(self):
        """주기적으로 스윙 후보에 대한 뉴스를 확인하고 매수를 트리거합니다."""
        while not self.shutdown_event.is_set():
            try:
                if not self.swing_candidates or not news_fetcher:
                    time.sleep(20)
                    continue

                logger.info(f"[NEWS-WORKER] {len(self.swing_candidates)}개 스윙 후보 뉴스 확인 시작...")
                for code, stock in self.swing_candidates.items():
                    news_item = news_fetcher.search_latest_news(stock['name'])
                    if news_item and news_item.get('published_at'):
                        if self.last_news_timestamp.get(code) != news_item['published_at']:
                            self.last_news_timestamp[code] = news_item['published_at']
                            news_item['query'] = stock['name']
                            on_news_event(
                                news_item=news_item,
                                swing_candidates=self.swing_candidates,
                                broker=self.account_manager,
                                position_mgr=self.position_manager,
                                cfg=self.config
                            )
                time.sleep(60)
            except Exception as e:
                logger.error(f"[NEWS-WORKER] 오류: {e}", exc_info=True)
                time.sleep(300)

    def _closing_price_buy_worker(self):
        """종가 매수 로직 (15:18 ~ 15:29), 점수 기반 Softmax 가중 배분 및 Limit-then-Market 적용"""
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_buy_time(now) and not self.buy_worker_done_today:
                    logger.info("[BUY_WORKER] 종가 매수 로직 시작 (Softmax + LTM 방식)")
                    trade_summary.weighted_allocation_used_today = True
                    
                    trading_config = self.config.get('trading', {})
                    top_n = trading_config.get('top_n_buy', 5)
                    tau = trading_config.get('softmax_tau', 10.0)
                    w_min = trading_config.get('weight_min', 0.10)
                    w_max = trading_config.get('weight_max', 0.35)

                    candidates = self.closing_price_candidates[:top_n]

                    if not candidates:
                        logger.warning("[BUY_WORKER] 최종 매수 후보군이 없습니다. 매수를 건너뜁니다.")
                        self.buy_worker_done_today = True
                        continue

                    logger.info("[BUY_WORKER] 매수 실행 직전, 최신 계좌 잔고를 조회합니다...")
                    initial_cash_balance = self.account_manager.get_simple_balance()
                    logger.info(f"[BUY_WORKER] 조회된 주문 가능 현금: {initial_cash_balance:,.0f}원")

                    if initial_cash_balance < 10000:
                        logger.warning(f"[BUY_WORKER] 주문 가능 현금이 {initial_cash_balance:,.0f}원으로 너무 적어 매수를 건너뜁니다.")
                        self.buy_worker_done_today = True
                        continue

                    logger.info(f"[BUY_WORKER] 총 {initial_cash_balance:,.0f}원의 현금으로 가중치 기반 예산 분배를 시작합니다.")

                    scores = np.array([c.get('total_score', 0.0) for c in candidates], dtype=float)
                    scores[scores == 0] = 1.0

                    z = scores / tau
                    weights = np.exp(z - np.max(z))
                    weights /= np.sum(weights)
                    weights = np.clip(weights, w_min, w_max)
                    weights /= np.sum(weights)
                    
                    logger.info(f"[BUY_WORKER] 최종 {len(candidates)}개 종목 매수 시작. 점수: {scores}, 가중치: {np.round(weights, 2)}")

                    buy_names = []
                    running_cash_balance = initial_cash_balance
                    for stock, weight in zip(candidates, weights):
                        code = stock['code']
                        name = stock['name']

                        if is_etf_like(name, code, trading_config):
                            logger.warning(f"[BUY_WORKER] 최종 매수 단계에서 ETF 유사 종목 필터링됨: {name} ({code})")
                            notifier.send_message(f"⚠️ 매수 제외(ETF 필터): {name}")
                            continue

                        budget_per_stock = initial_cash_balance * weight
                        
                        quote_info = self.market_cache.get_quote_full(code)
                        if not quote_info or not quote_info.get('ask_price', 0) > 0:
                            logger.warning(f"[BUY_WORKER] {name} ({code}) 호가 정보가 없어 시장가로 주문합니다.")
                            current_price = quote_info.get('price', 0) if quote_info else 0
                            if current_price > 0:
                                shares = int(budget_per_stock // current_price)
                                required_cash = shares * current_price
                                if running_cash_balance < required_cash:
                                    logger.warning(f"[BUY_WORKER] {name} ({code}) 필요금액({required_cash:,.0f})이 잔고({running_cash_balance:,.0f})를 초과하여 시장가 매수를 건너뜁니다.")
                                    continue
                                
                                if shares > 0:
                                    result = self.account_manager.place_buy_order_market(code, shares)
                                    if result and result.get('success'):
                                        logger.info(f"[BUY] 시장가 매수 주문 성공: {name} ({code}) {shares}주")
                                        running_cash_balance -= required_cash
                                        self.position_manager.add_position(code, shares, current_price, name)
                                        trade_summary.record_trade(
                                            code=code, name=name, action='BUY', quantity=shares, price=current_price,
                                            order_id=result.get('order_id', ''), strategy='ClosingPrice_Market',
                                            weight=weight
                                        )
                                        buy_names.append(name)
                            continue

                        best_ask = quote_info.get('ask_price', 0)

                        if best_ask > 0:
                            shares = int(budget_per_stock // best_ask)
                            required_cash = shares * best_ask
                            if running_cash_balance < required_cash:
                                logger.warning(f"[BUY_WORKER] {name} ({code}) 필요금액({required_cash:,.0f})이 잔고({running_cash_balance:,.0f})를 초과하여 LTM 매수를 건너뜁니다.")
                                continue

                            if shares > 0:
                                logger.info(f"[BUY_WORKER] {name} ({code}) {shares}주 매수 시도 (지정가: {best_ask})")
                                result = self.account_manager.place_buy_with_limit_then_market(
                                    stock_code=code,
                                    quantity=shares,
                                    limit_price=best_ask
                                )
                                
                                if result.ok and result.filled_qty > 0:
                                    filled_amount = result.filled_qty * best_ask # LTM이므로 지정가 기준으로 차감
                                    running_cash_balance -= filled_amount
                                    logger.info(f"[BUY] LTM 매수 성공: {name} ({code}) {result.filled_qty}주. 메시지: {result.msg}")
                                    self.position_manager.add_position(code, result.filled_qty, best_ask, name)
                                    trade_summary.record_trade(
                                        code=code, name=name, action='BUY', quantity=result.filled_qty, price=best_ask,
                                        order_id=result.order_id, strategy='ClosingPrice_LTM',
                                        weight=weight
                                    )
                                    buy_names.append(name)
                                else:
                                    logger.error(f"[BUY] LTM 매수 최종 실패: {name} ({code}). 메시지: {result.msg}")
                        else:
                            logger.warn(f"[BUY_WORKER] {name} ({code}) 최우선 매도 호가를 찾을 수 없어 매수를 건너뜁니다.")

                    if buy_names:
                        notifier.send_message(f"종가 매수 완료 (LTM 방식): {', '.join(buy_names)}")

                    self.buy_worker_done_today = True
                    logger.info("[BUY_WORKER] 종가 매수 로직 완료")
                time.sleep(10)
            except Exception as e:
                logger.error(f"[BUY_WORKER] 오류: {e}", exc_info=True)
                time.sleep(60)

    def _update_subscriptions(self, new_codes: Set[str]):
        if not self.ws_manager or not self.ws_manager.is_connected:
            logger.warning("[SUB_MGR] 웹소켓이 연결되지 않아 구독을 업데이트할 수 없습니다.")
            return

        owned_codes = set(self.position_manager.positions.keys())
        required_codes = new_codes.union(owned_codes)

        codes_to_add = required_codes - self.subscribed_codes
        codes_to_remove = self.subscribed_codes - required_codes

        if codes_to_add:
            logger.info(f"[SUB_MCR] 신규 구독 추가: {list(codes_to_add)}")
            for code in codes_to_add:
                self.ws_manager.subscribe(code)
                time.sleep(0.3)
        
        if codes_to_remove:
            logger.info(f"[SUB_MGR] 기존 구독 해지: {list(codes_to_remove)}")
            for code in codes_to_remove:
                self.ws_manager.unsubscribe(code)
                time.sleep(0.3)
        
        self.subscribed_codes = required_codes

    def _wait_and_connect_ws(self) -> bool:
        logger.info("[SYSTEM] 장 시작(09:00)까지 대기하며, 08:58에 웹소켓 연결을 시도합니다.")
        while not self.shutdown_event.is_set():
            now = datetime.now()
            if now.weekday() < 5 and now.time() >= dt_time(8, 58):
                logger.info("[SYSTEM] 장 시작 시간이 임박하여 웹소켓 연결을 시작합니다.")
                try:
                    self.ws_manager.start()
                    if not self.ws_manager.wait_for_connection(timeout=15):
                        raise Exception("웹소켓 연결 시간 초과")
                    logger.info("[SYSTEM] 웹소켓 연결 성공.")
                    return True
                except Exception as e:
                    logger.error(f"[SYSTEM] 장 시작 전 웹소켓 연결 실패: {e}", exc_info=True)
                    return False
            time.sleep(10)
        logger.info("[SYSTEM] 웹소켓 연결 대기 중 시스템 종료 신호 수신.")
        return False

    def shutdown(self):
        if not self.shutdown_event.is_set():
            logger.info("[SYSTEM] 시스템 종료 시작")
            self.shutdown_event.set()
            if self.ws_manager:
                self.ws_manager.stop()
            data_logger.shutdown()
            event_logger.shutdown()
            notifier.send_message("시스템 종료")

    def _signal_handler(self, signum, frame):
        self.shutdown()

    def print_summary(self, date_str: Optional[str] = None):
        pass

def load_config() -> Dict:
    """전역 config 객체에서 필요한 설정들을 딕셔너리로 묶어 반환합니다."""
    try:
        config.print_config_summary()
        return {
            'api': config.get_kis_config(),
            'telegram': config.get_telegram_config(),
            'trading': config.get_trading_config(),
            'system': config.get('system', {})
        }
    except Exception as e:
        logger.error(f"[CONFIG] 설정 로드 실패: {e}", exc_info=True)
        return {}