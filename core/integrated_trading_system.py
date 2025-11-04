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
from strategies.dynamic_screener import DynamicScreener
from strategies.strategy_engine import (
    StrategyEngine,
    MovingAverageCrossoverStrategy,
    RSISwingStrategy,
    BollingerMeanReversionStrategy,
)
from strategies.risk_management import PortfolioRiskManager
from data.data_logger import data_logger
from data.event_logger import event_logger
from data.market_data_provider import KISMarketDataProvider
from web_socket.web_socket_manager import KISWebSocketClient
from web_socket.market_cache import init_market_cache
from core.config import config
from core.position_manager import RealPositionManager
from utils.balance_manager import BalanceManager
from utils.news_fetcher import news_fetcher

logger = logging.getLogger(__name__)

class IntegratedTradingSystem:
    # KIS 스캘핑 통합 시스템 컨트롤러
    
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
        self.strategy_settings = self.config.get('strategy', {})
        self.market_data_provider = None
        self.dynamic_screener: Optional[DynamicScreener] = None
        self.strategy_engine: Optional[StrategyEngine] = None
        self.portfolio_risk_manager: Optional[PortfolioRiskManager] = None
        logger.info("[SYSTEM] 통합 스캘핑 시스템 초기 구성 시작")

    def _normalize_code(self, code: str) -> str:
        return f"A{str(code).lstrip('A').zfill(6)}"

    def initialize(self) -> bool:
        try:
            logger.info("[SYSTEM] 하위 모듈 초기화 진행")
            api_config = self.config.get('api', {})
            self.account_manager = init_account_manager(
                api_config['app_key'], api_config['app_secret'], api_config['account_no']
            )
            if not (self.account_manager and self.account_manager.api.access_token):
                raise Exception("API 인증 정보 확인에 실패했습니다")
            logger.info("[SYSTEM] API 인증 정보 확인 완료")

            try:
                sector_overrides = self.strategy_settings.get('sector_filter', {}).get('sector_overrides', {})
                sector_symbols = sorted({value for value in sector_overrides.values() if value})
                self.market_data_provider = KISMarketDataProvider(self.account_manager, sector_symbols=sector_symbols)
                self.dynamic_screener = DynamicScreener(self.market_data_provider, self.strategy_settings, news_fetcher)
                self.strategy_engine = StrategyEngine([
                    MovingAverageCrossoverStrategy(),
                    RSISwingStrategy(),
                    BollingerMeanReversionStrategy(),
                ])
                self.portfolio_risk_manager = PortfolioRiskManager(self.strategy_settings.get('risk_management', {}))
                logger.info('[SYSTEM] KIS 기반 스크리너와 전략 엔진 초기화 완료')
            except Exception as data_exc:
                logger.warning('[SYSTEM] 시장 데이터 공급원 초기화 실패: %s', data_exc)
                self.market_data_provider = None
                self.dynamic_screener = None
                self.strategy_engine = None
                self.portfolio_risk_manager = None
            self.market_cache = init_market_cache(self.config, self.position_manager, self.account_manager)
            setattr(self.account_manager, "market_cache", self.market_cache)

            self.beginning_total_assets = self.account_manager.get_total_assets()
            if self.beginning_total_assets == 0:
                logger.error("[SYSTEM] 시작 총자산 조회에 실패하여 시스템을 중단합니다")
                return False

            cash_balance = self.account_manager.get_simple_balance()
            self.balance_manager.set_balance(cash_balance)
            trade_summary.set_starting_balance(self.beginning_total_assets)
            logger.info(f"[SYSTEM] 시작 총자산: {self.beginning_total_assets:,}원 | 현금: {cash_balance:,}원")

            current_positions = self.account_manager.get_current_positions()
            codes_to_subscribe = set()
            if current_positions:
                logger.info(f"[SYSTEM] 기존 보유 종목 {len(current_positions)}개 확인")
                for pos in current_positions:
                    code = self._normalize_code(pos.get('pdno'))
                    self.position_manager.add_position(code, int(pos.get('hldg_qty')), float(pos.get('pchs_avg_pric')), pos.get('prdt_name'))
                    codes_to_subscribe.add(code)
                logger.info(f"[SYSTEM] 보유 종목 구독 복원 완료: {list(codes_to_subscribe)}")
            
            approval_key = self.account_manager.api.get_approval_key()
            if not approval_key: raise Exception("승인 키 발급에 실패했습니다")

            self.ws_manager = KISWebSocketClient(config=self.config, account_manager=self.account_manager, approval_key=approval_key, codes=codes_to_subscribe, market_cache=self.market_cache)
            self.subscribed_codes.update(codes_to_subscribe)
            logger.info(f"[SYSTEM] 초기화 완료 - 구독 중인 종목 수: {len(self.subscribed_codes)}")
            return True
            
        except Exception as e:
            logger.error(f"[SYSTEM] 초기화 중 예외 발생: {e}", exc_info=True)
            return False

    def run(self):
        if not self.initialize():
            self.shutdown()
            return False

        if not self._wait_and_connect_ws():
            logger.error("[SYSTEM] 웹소켓 연결에 실패했습니다")
            self.shutdown()
            return False

        logger.info("[SYSTEM] 메인 실행 루프 진입")
        self._start_workers()
        
        try:
            while not self.shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("[SYSTEM] 키보드 인터럽트를 감지하여 종료합니다")
        finally:
            self.shutdown()
        return True

    def _start_workers(self):
        threading.Thread(target=self._opening_sell_worker, daemon=True).start()
        threading.Thread(target=self._closing_price_screening_worker, daemon=True).start()
        threading.Thread(target=self._closing_price_buy_worker, daemon=True).start()
        threading.Thread(target=self._news_event_worker, daemon=True).start()
        threading.Thread(target=self._daily_reset_worker, daemon=True).start()
        logger.info("[WORKER] Background workers started")

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
                    logger.info("[SYSTEM] 자정 리셋: 일일 상태 플래그를 초기화합니다")
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
                                logger.info(f"[SELL_WORKER] {position['name']} 시초가 확보: {open_price}")
                            else: 
                                self.sell_open_prices[code] = position.get('price', 0)
                                self.sell_peaks[code] = position.get('price', 0)
                                logger.warning(f"[SELL_WORKER] {position['name']} 시초가 조회 실패, 보유 평균가를 사용합니다")

                    if not self.positions_to_sell:
                        if not self.sell_worker_done_today:
                            logger.info("[SELL_WORKER] 매도 대상이 없어 오늘 매도 작업을 종료합니다")
                            self.sell_worker_done_today = True
                        continue

                    positions_to_check = list(self.positions_to_sell.keys())
                    for code in positions_to_check:
                        quote = self.market_cache.get_quote_full(code)
                        if quote and quote.get('price') > 0:
                            self._check_sell_conditions(code, quote.get('price'))
                
                if now.time() >= dt_time(15, 20) and not self.sell_worker_done_today:
                    logger.info("[SELL_WORKER] 장 마감으로 매도 워커를 종료합니다")
                    if self.positions_to_sell:
                        logger.info(f"[SELL_WORKER] 미처리 종목: {list(self.positions_to_sell.keys())}")
                    self.sell_worker_done_today = True

                time.sleep(2)
            except Exception as e:
                logger.error(f"[SELL_WORKER] 예외 발생: {e}", exc_info=True)
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
            self._execute_sell(code, f"Trailing Stop (수익률 {profit:.2%})")
            return

        open_price = self.sell_open_prices.get(code, 0)
        if open_price > 0:
            open_fail_drop_ratio = trading_config.get('open_fail_drop_ratio', 0.99)
            if profit < min_profit_pct and current_price < (open_price * open_fail_drop_ratio):
                self._execute_sell(code, f"Open Fail Stop (수익률 {(current_price/open_price-1):.2%})")
                return

    def _execute_sell(self, code: str, reason: str):
        if code not in self.positions_to_sell: return

        pos = self.positions_to_sell[code]
        req_shares = int(pos['shares'])
        logger.info(f"[SELL] 매도 조건 충족: {pos['name']} ({code}) - 사유 {reason}, 요청 수량 {req_shares}")

        # 현재 보유/주문 가능 수량 확인
        try:
            holdings = self.account_manager.get_current_positions()
            avail = 0
            for h in holdings:
                if self._normalize_code(h.get('pdno')) == code:
                    avail = int(h.get('ord_psbl_qty') or h.get('hldg_qty') or 0)
                    logger.info(f"[SELL] {pos['name']} available quantity: {avail}")
                    break
        except Exception as e:
            logger.error(f"[SELL] {pos['name']} 보유 수량 조회 실패: {e}", exc_info=True)
            avail = 0  # 조회 실패 시 매도 제외

        sell_qty = max(0, min(req_shares, avail))
        if sell_qty <= 0:
            logger.warning(f"[SELL] {pos['name']} ({code}) available=0 (requested: {req_shares}); skipping sell")
            # 매도할 수량이 없으면 대기 목록에서 제거
            del self.positions_to_sell[code]
            return

        if sell_qty < req_shares:
            logger.warning(f"[SELL] {pos['name']} ({code}) 요청 {req_shares} > 보유 {avail}, 실제 매도 {sell_qty}주")

        result = self.account_manager.place_sell_order_market(code, sell_qty)
        if result and result.get('success'):
            current_price = self.market_cache.get_quote(code) or pos.get('price', 0)
            self.position_manager.close_position(
                code=code, quantity=sell_qty, price=current_price, reason=reason, name=pos['name']
            )
            logger.info(f"[SELL] Market sell submitted: {pos['name']} ({code}) {sell_qty} shares")
            del self.positions_to_sell[code]
        else:
            # 주문 실패 시 전체 응답을 기록
            error_msg = result.get('error', 'Unknown error')
            full_response = result.get('full_response', {})
            logger.error(f"[SELL] 시장가 매도 실패: {pos['name']} ({code}), 메시지: {error_msg}, 응답: {full_response}")

    def _safe_int(self, value) -> int:
        if isinstance(value, int):
            return value
        try:
            # API가 문자열을 반환하는 경우 쉼표를 제거
            return int(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return 0

    def _normalize_stock(self, rec: Dict) -> Dict:
        # Normalize stock records coming from various KIS API payloads
        name = rec.get("name") or rec.get("stock_name") or rec.get("hts_kor_isnm") or ""
        code = rec.get("code") or rec.get("symbol") or rec.get("mksc_shrn_iscd") or rec.get("srtn_cd") or ""
        rank = rec.get("volume_rank") or rec.get("rank") or rec.get("stck_ranking") or None

        # API 응답의 다양한 필드에서 거래대금 값을 추출
        turnover = rec.get("turnover") or rec.get("acml_tr_pbmn") or rec.get("acc_trdval") or 0

        return {"name": name, "code": code, "volume_rank": rank, "turnover": self._safe_int(turnover), **rec}

    def _extract_universe_symbols(self, turnover_stocks: List[Dict]) -> List[str]:
        base_universe = self.strategy_settings.get('universe', {}).get('default_universe', [])
        symbols = []
        for stock in turnover_stocks:
            code = stock.get('code') or stock.get('mksc_shrn_iscd') or stock.get('srtn_cd') or stock.get('symbol')
            if not code:
                continue
            normalized = str(code).lstrip('A')
            if normalized not in symbols:
                symbols.append(normalized)
        combined = list(dict.fromkeys(base_universe + symbols))
        return combined

    def _report_dynamic_screening(self, result) -> None:
        try:
            top_n = 5
            leaders = ", ".join(result.sector_leaders) if result.sector_leaders else "정보 없음"
            message_lines = [
                "*동적 스크리닝 요약*",
                f"시장 방향성: {result.market_bias} / 리더 섹터: {leaders}",
                "\n*마감 매수 후보*"
            ]
            if result.closing_candidates:
                for idx, cand in enumerate(result.closing_candidates[:top_n]):
                    message_lines.append(
                        f"{idx+1}. {cand.name} ({cand.symbol}) - 점수 {cand.score:.1f} / 추세 {cand.metadata.get('trend_bias')}"
                    )
                    for news in cand.news:
                        message_lines.append(
                            f"    - {news.get('timestamp', '')} {news.get('title', '')} {news.get('link', '')}"
                        )
            else:
                message_lines.append("- 없음")
            message_lines.append("\n*스윙 후보*")
            if result.swing_candidates:
                for idx, cand in enumerate(result.swing_candidates[:top_n]):
                    message_lines.append(
                        f"{idx+1}. {cand.name} ({cand.symbol}) - 점수 {cand.score:.1f} / 추세 {cand.metadata.get('trend_bias')}"
                    )
                    for news in cand.news:
                        message_lines.append(
                            f"    - {news.get('timestamp', '')} {news.get('title', '')} {news.get('link', '')}"
                        )
            else:
                message_lines.append("- 없음")
            notifier.send_message("\n".join(message_lines))
        except Exception as exc:
            logger.error("[SCREENER] 동적 스크리닝 리포트 작성 실패: %s", exc, exc_info=True)

    def _legacy_screen(self, turnover_stocks: List[Dict]) -> None:
        def _append_news_line(lines, name):
            if not news_fetcher:
                return
            try:
                n = news_fetcher.search_latest_news(name)
                if n and n.get("title"):
                    ts = n.get("timestamp", "")
                    lines.append(f"    - {ts} {n['title']} {n['link']}")
            except Exception:
                pass

        swing_candidates_list = get_swing_candidates(turnover_stocks, self.config, self.market_cache)
        self.swing_candidates = {s['code']: s for s in swing_candidates_list}

        self.closing_price_candidates = closing_price_stock_filter(
            self.market_cache, turnover_stocks, self.account_manager.api
        )

        if not self.closing_price_candidates and turnover_stocks:
            logger.info("[SCREENER] 마감 후보가 없어 거래대금 상위 5종목을 대체로 사용합니다")

            def fallback_from_volume(volume_top: List[Dict], top_k: int) -> List[Dict]:
                trading_config = self.config.get('trading', {})
                fallback_candidates = []
                for stock in volume_top:
                    if is_etf_like(stock.get('name', ''), stock.get('code', ''), trading_config):
                        continue
                    if stock.get('turnover', 0) > 0:
                        fallback_candidates.append({
                            'code': stock.get('code'),
                            'name': stock.get('name', ''),
                            'turnover': stock.get('turnover', 0),
                            'total_score': 1.0,
                            'scores': {},
                            'reason': 'fallback_volume'
                        })
                    if len(fallback_candidates) >= top_k:
                        break
                return fallback_candidates

            self.closing_price_candidates = fallback_from_volume(turnover_stocks, top_k=5)

        logger.info(f"[SCREENER] 마감 매수 후보 수: {len(self.closing_price_candidates)}")
        logger.info(f"[SCREENER] 스윙 후보 수: {len(self.swing_candidates)}")

        if self.closing_price_candidates or self.swing_candidates:
            top_n = 5
            message_lines = ["*일간 스크리닝 요약*"]
            message_lines.append("\n*마감 매수 후보*")
            if self.closing_price_candidates:
                for i, stock in enumerate(self.closing_price_candidates[:top_n]):
                    line = f"{i+1}. {stock.get('name', 'N/A')} ({stock.get('code', 'N/A')}) - 거래대금 순위 {stock.get('volume_rank', 'N/A')}"
                    message_lines.append(line)
            else:
                message_lines.append("- 없음")
            message_lines.append("\n*스윙 후보*")
            if self.swing_candidates:
                for i, stock in enumerate(list(self.swing_candidates.values())[:top_n]):
                    line = f"{i+1}. {stock.get('name', 'N/A')} ({stock.get('code', 'N/A')}) - 모멘텀 {stock.get('score', 0):.1f}"
                    message_lines.append(line)
            else:
                message_lines.append("- 없음")
            notifier.send_message("\n".join(message_lines))
        else:
            no_data_msg = "[SCREENER] 이번 사이클에서 후보를 찾지 못했습니다"
            logger.info(no_data_msg)
            notifier.send_message(no_data_msg)

    def _build_trade_plan(self, code: str, price: float, desired_cash: float):
        if not (self.strategy_engine and self.market_data_provider and self.portfolio_risk_manager):
            return None

        try:
            history = self.market_data_provider.get_daily_history(code, lookback_days=240)
            if history.empty or price <= 0:
                return None

            risk_cfg = dict(self.strategy_settings.get('risk_management', {}))
            risk_cfg.update(self.strategy_settings.get('execution', {}))
            partial_plan = self.portfolio_risk_manager.build_partial_exit_plan(price)
            risk_cfg['partial_exit_plan'] = partial_plan

            trade_plans = self.strategy_engine.build_trade_plan(code, history, 1, risk_cfg)
            if not trade_plans:
                return None

            for plan in trade_plans:
                if plan.action != 'BUY':
                    continue
                portfolio_value = self.account_manager.get_total_assets()
                sizing = self.portfolio_risk_manager.calculate_position_size(price, plan.atr, portfolio_value)
                if sizing.quantity <= 0:
                    continue
                max_qty_by_cash = int(desired_cash // price)
                quantity = max(0, min(sizing.quantity, max_qty_by_cash))
                if quantity <= 0:
                    continue
                plan.quantity = quantity
                plan.price = price
                return plan
        except Exception as exc:
            logger.error(f"[BUY_WORKER] 트레이드 플랜 생성 중 예외 발생: {exc}", exc_info=True)
        return None



    def _closing_price_screening_worker(self):
        # 종가 스크리닝 작업자 (09:30 ~ 15:20)

        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_screening_time(now):
                    logger.info("[SCREENER] 장중 종가 스크리닝을 실행합니다")

                    turnover_stocks = self.account_manager.get_turnover_ranking(count=100) or []
                    turnover_count = len(turnover_stocks)
                    if turnover_count == 0:
                        logger.warning("[SCREENER] 거래대금 상위 목록을 가져오지 못했습니다. API 응답이 비어 있거나 필터링되었습니다.")
                    else:
                        sample_codes = [s.get('code') for s in turnover_stocks[:5]]
                        logger.info(f"[SCREENER] 거래대금 상위 {turnover_count}개 수신 (예시: {sample_codes})")
                    universe = self._extract_universe_symbols(turnover_stocks)
                    code_name_map = {}
                    for stock in turnover_stocks:
                        code = stock.get('code') or stock.get('mksc_shrn_iscd') or stock.get('srtn_cd') or stock.get('symbol')
                        if code:
                            normalized = str(code).lstrip('A')
                            code_name_map[normalized] = stock.get('name') or stock.get('hts_kor_isnm') or normalized

                    used_dynamic = False
                    if self.dynamic_screener:
                        logger.info("[SCREENER] 동적 스크리너 대상 %d종목", len(universe))
                        result = self.dynamic_screener.screen(universe)
                        if result.closing_candidates or result.swing_candidates:
                            used_dynamic = True
                            self._report_dynamic_screening(result)

                            self.closing_price_candidates = []
                            for cand in result.closing_candidates:
                                cand_dict = cand.to_dict()
                                symbol = cand.symbol
                                cand_dict['name'] = code_name_map.get(symbol, cand_dict.get('name', symbol))
                                self.closing_price_candidates.append(cand_dict)

                            self.swing_candidates = {}
                            for cand in result.swing_candidates:
                                cand_dict = cand.to_dict()
                                symbol = cand.symbol
                                cand_dict['name'] = code_name_map.get(symbol, cand_dict.get('name', symbol))
                                self.swing_candidates[cand.symbol] = cand_dict
                        else:
                            logger.info("[SCREENER] 동적 스크리너 결과가 없어 기존 규칙을 사용합니다")

                    if not used_dynamic:
                        self._legacy_screen(turnover_stocks)

                    closing_codes = {self._normalize_code(c['code']) for c in self.closing_price_candidates}
                    swing_codes = {self._normalize_code(c['code']) for c in self.swing_candidates.values()}
                    self._update_subscriptions(closing_codes.union(swing_codes))

                time.sleep(300)
            except Exception as e:
                logger.error(f"[SCREENER] 스크리닝 워커 예외: {e}", exc_info=True)
                time.sleep(300)

    def _news_event_worker(self):
        # Background worker handling news-driven swing entries
        while not self.shutdown_event.is_set():
            try:
                if not self.swing_candidates or not news_fetcher:
                    time.sleep(20)
                    continue

                logger.info(f"[NEWS-WORKER] 스윙 후보 {len(self.swing_candidates)}개 뉴스 확인")
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
                logger.error(f"[NEWS-WORKER] 예외 발생: {e}", exc_info=True)
                time.sleep(300)

    def _closing_price_buy_worker(self):
        # 장 마감 매수 로직 (15:18 ~ 15:29) - 소프트맥스 비중 및 LTM 주문
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_buy_time(now) and not self.buy_worker_done_today:
                    logger.info("[BUY_WORKER] 장 마감 매수 로직 실행 (Softmax + LTM)")
                    trade_summary.weighted_allocation_used_today = True
                    
                    trading_config = self.config.get('trading', {})
                    top_n = trading_config.get('top_n_buy', 5)
                    tau = trading_config.get('softmax_tau', 10.0)
                    w_min = trading_config.get('weight_min', 0.10)
                    w_max = trading_config.get('weight_max', 0.35)

                    candidates = self.closing_price_candidates[:top_n]

                    if not candidates:
                        logger.warning("[BUY_WORKER] 최종 매수 후보가 없어 매수 작업을 건너뜁니다")
                        self.buy_worker_done_today = True
                        continue

                    logger.info("[BUY_WORKER] 매수 실행 전 최신 계좌 잔고를 조회합니다")
                    initial_cash_balance = self.account_manager.get_simple_balance()
                    logger.info(f"[BUY_WORKER] 현재 가용 현금: {initial_cash_balance:,.0f}원")

                    if initial_cash_balance < 10000:
                        logger.warning(f"[BUY_WORKER] 주문 가능 금액이 {initial_cash_balance:,.0f}원으로 부족해 매수를 생략합니다")
                        self.buy_worker_done_today = True
                        continue

                    logger.info("[BUY_WORKER] 가용 현금을 기준으로 소프트맥스 비중을 계산합니다")

                    scores = np.array([c.get('total_score', 0.0) for c in candidates], dtype=float)
                    scores[scores == 0] = 1.0

                    z = scores / tau
                    weights = np.exp(z - np.max(z))
                    weights /= np.sum(weights)
                    weights = np.clip(weights, w_min, w_max)
                    weights /= np.sum(weights)
                    
                    logger.info(f"[BUY_WORKER] 최종 {len(candidates)}종목 매수 후보 점수 {scores}, 가중치: {np.round(weights, 2)}")

                    buy_names = []
                    running_cash_balance = initial_cash_balance
                    for stock, weight in zip(candidates, weights):
                        code = stock['code']
                        name = stock['name']

                        if is_etf_like(name, code, trading_config):
                            logger.warning(f"[BUY_WORKER] 최종 매수 후보에서 ETF 유사 종목 제외: {name} ({code})")
                            notifier.send_message(f"장 마감 매수 제외: ETF로 분류된 종목 {name}")
                            continue

                        budget_per_stock = initial_cash_balance * weight
                        code_clean = str(code).lstrip('A')

                        quote_info = self.market_cache.get_quote_full(code)
                        best_ask = quote_info.get('ask_price', 0) if quote_info else 0
                        current_price = quote_info.get('price', 0) if quote_info else 0
                        order_price = best_ask if best_ask > 0 else current_price

                        if order_price <= 0:
                            logger.warning(f"[BUY_WORKER] {name} ({code}) 호가 데이터 부족으로 매수를 건너뜁니다")
                            continue

                        trade_plan = self._build_trade_plan(code_clean, order_price, budget_per_stock)
                        if trade_plan:
                            shares = trade_plan.quantity
                            order_mode = trade_plan.order_type
                            strategy_name = trade_plan.strategy
                        else:
                            shares = int(budget_per_stock // order_price)
                            order_mode = 'limit' if best_ask > 0 else 'market'
                            strategy_name = 'ClosingPrice'

                        if shares <= 0:
                            logger.warning(f"[BUY_WORKER] {name} ({code}) 계산된 수량이 0이라 매수를 생략합니다")
                            continue

                        required_cash = shares * order_price
                        if running_cash_balance < required_cash:
                            logger.warning(
                                f"[BUY_WORKER] {name} ({code}) 필요 자금 {required_cash:,.0f}원 > 잔여 현금 {running_cash_balance:,.0f}원, 매수를 생략합니다"
                            )
                            continue

                        if order_mode == 'market' or best_ask <= 0:
                            result = self.account_manager.place_buy_order_market(code, shares)
                            if result and result.get('success'):
                                logger.info(f"[BUY] 시장가 매수 체결 완료: {name} ({code}) {shares}주")
                                running_cash_balance -= required_cash
                                self.position_manager.add_position(code, shares, order_price, name)
                                trade_summary.record_trade(
                                    code=code, name=name, action='BUY', quantity=shares, price=order_price,
                                    order_id=result.get('order_id', ''), strategy=strategy_name,
                                    weight=weight
                                )
                                if trade_plan:
                                    stop_info = f"{trade_plan.stop_loss:.2f}" if trade_plan.stop_loss else "N/A"
                                    target_info = f"{trade_plan.take_profit:.2f}" if trade_plan.take_profit else "N/A"
                                    logger.info(f"[BUY] 손절 {stop_info} / 목표가 {target_info}")
                                    if trade_plan.partial_exit:
                                        logger.info(f"[BUY] 부분 청산 계획: {trade_plan.partial_exit}")
                                buy_names.append(name)
                        else:
                            logger.info(f"[BUY_WORKER] {name} ({code}) {shares}주 매수 시도 (호가: {best_ask})")
                            result = self.account_manager.place_buy_with_limit_then_market(
                                stock_code=code,
                                quantity=shares,
                                limit_price=best_ask
                            )

                            if result.ok and result.filled_qty > 0:
                                filled_amount = result.filled_qty * best_ask
                                running_cash_balance -= filled_amount
                                logger.info(f"[BUY] LTM 매수 체결: {name} ({code}) {result.filled_qty}주, 메시지: {result.msg}")
                                self.position_manager.add_position(code, result.filled_qty, best_ask, name)
                                trade_summary.record_trade(
                                    code=code, name=name, action='BUY', quantity=result.filled_qty, price=best_ask,
                                    order_id=result.order_id, strategy=strategy_name,
                                    weight=weight
                                )
                                if trade_plan:
                                    stop_info = f"{trade_plan.stop_loss:.2f}" if trade_plan.stop_loss else "N/A"
                                    target_info = f"{trade_plan.take_profit:.2f}" if trade_plan.take_profit else "N/A"
                                    logger.info(f"[BUY] 손절 {stop_info} / 목표가 {target_info}")
                                    if trade_plan.partial_exit:
                                        logger.info(f"[BUY] 부분 청산 계획: {trade_plan.partial_exit}")
                                buy_names.append(name)
                            else:
                                logger.error(f"[BUY] LTM 매수 실패: {name} ({code}). 메시지: {result.msg}")

                    if buy_names:
                        notifier.send_message(f"장 마감 매수 완료(LTM 포함): {', '.join(buy_names)}")

                    self.buy_worker_done_today = True
                    logger.info("[BUY_WORKER] 금일 장 마감 매수 작업을 마쳤습니다")
                time.sleep(10)
            except Exception as e:
                logger.error(f"[BUY_WORKER] 예외 발생: {e}", exc_info=True)
                time.sleep(60)

    def _update_subscriptions(self, new_codes: Set[str]):
        if not self.ws_manager or not self.ws_manager.is_connected:
            logger.warning("[SUB_MGR] 웹소켓이 연결되지 않아 구독을 갱신할 수 없습니다")
            return

        owned_codes = set(self.position_manager.positions.keys())
        required_codes = new_codes.union(owned_codes)

        codes_to_add = required_codes - self.subscribed_codes
        codes_to_remove = self.subscribed_codes - required_codes

        if codes_to_add:
            logger.info(f"[SUB_MGR] 신규 구독 추가: {list(codes_to_add)}")
            for code in codes_to_add:
                self.ws_manager.subscribe(code)
                time.sleep(0.3)
        
        if codes_to_remove:
            logger.info(f"[SUB_MGR] 구독 해제: {list(codes_to_remove)}")
            for code in codes_to_remove:
                self.ws_manager.unsubscribe(code)
                time.sleep(0.3)
        
        self.subscribed_codes = required_codes

    def _wait_and_connect_ws(self) -> bool:
        logger.info("[SYSTEM] 장 시작(09:00)까지 대기하며 08:58에 웹소켓 연결을 시도합니다")
        while not self.shutdown_event.is_set():
            now = datetime.now()
            if now.weekday() < 5 and now.time() >= dt_time(8, 58):
                logger.info("[SYSTEM] 조건을 충족하여 웹소켓 연결을 시도합니다")
                try:
                    self.ws_manager.start()
                    if not self.ws_manager.wait_for_connection(timeout=15):
                        raise Exception("웹소켓 연결 대기 시간이 초과되었습니다")
                    logger.info("[SYSTEM] 웹소켓 연결 성공")
                    return True
                except Exception as e:
                    logger.error(f"[SYSTEM] 웹소켓 연결 중 예외 발생: {e}", exc_info=True)
                    return False
            time.sleep(10)
        logger.info("[SYSTEM] 웹소켓 연결 시도가 종료 신호로 중단되었습니다")
        return False

    def shutdown(self):
        if not self.shutdown_event.is_set():
            logger.info("[SYSTEM] 종료 이벤트 플래그를 설정합니다")
            self.shutdown_event.set()
            logger.info("[SYSTEM] 시스템 종료 절차를 시작합니다")
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
    # 설정 조각을 하나의 딕셔너리로 합치기
    try:
        config.print_config_summary()
        return {
            'api': config.get_kis_config(),
            'telegram': config.get_telegram_config(),
            'trading': config.get_trading_config(),
            'system': config.get('system', {}),
            'strategy': config.get_strategy_settings()
        }
    except Exception as e:
        logger.error(f"[CONFIG] 설정 로드 실패: {e}", exc_info=True)
        return {}




