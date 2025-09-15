import threading
import time
import signal
import logging
import traceback
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Set
import numpy as np

from api.account_manager import init_account_manager
from analytics.trade_summary import trade_summary
from utils.notifier import notifier
from strategies.closing_price_trader import closing_price_stock_filter # 신규 종가매매 스크리너
from utils.code_loader import code_loader
from data.data_logger import data_logger
from data.event_logger import event_logger
from web_socket.web_socket_manager import KISWebSocketClient
from web_socket.market_cache import init_market_cache    
from core.config import config
from core.position_manager import RealPositionManager
from utils.balance_manager import BalanceManager

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

        # 종가 매매 전략용 상태 변수
        self.closing_price_candidates: List[Dict] = []
        self.sell_worker_done_today = False
        self.buy_worker_done_today = False
        
        # 익일 매도 전략용 상태 변수
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
            
            # ... (기존 데이터 로딩 로직 유지) ...

            self.beginning_total_assets = self.account_manager.get_total_assets()
            if self.beginning_total_assets == 0:
                logger.error("[SYSTEM] 시작 총자산 조회 실패. 시스템을 시작할 수 없습니다.")
                return False

            cash_balance = self.account_manager.get_simple_balance()
            self.balance_manager.set_balance(cash_balance)
            trade_summary.set_starting_balance(self.beginning_total_assets)
            logger.info(f"[SYSTEM] 시작 총자산: {self.beginning_total_assets:,}원, 현금: {cash_balance:,}원")

            # 보유 종목 복원 및 구독 준비
            current_positions = self.account_manager.get_current_positions()
            codes_to_subscribe = set()
            if current_positions:
                logger.info(f"[SYSTEM] {len(current_positions)}개 보유 종목 발견")
                for pos in current_positions:
                    code = self._normalize_code(pos.get('pdno'))
                    self.position_manager.add_position(code, int(pos.get('hldg_qty')), float(pos.get('pchs_avg_pric')), pos.get('prdt_name'))
                    codes_to_subscribe.add(code)
                logger.info(f"[SYSTEM] 보유 종목 포지션 복원 완료: {list(codes_to_subscribe)}")
            
            # 웹소켓 승인 키 발급
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
        threading.Thread(target=self._daily_reset_worker, daemon=True).start()
        logger.info("[WORKER] 모든 워커 시작 완료")

    # --- 시간대별 로직 제어 --- #
    def _is_sell_time(self, now: datetime) -> bool:
        return dt_time(9, 0) <= now.time() < dt_time(9, 30)

    def _is_screening_time(self, now: datetime) -> bool:
        return dt_time(9, 30) <= now.time() < dt_time(15, 20)

    def _is_buy_time(self, now: datetime) -> bool:
        return now.time() >= dt_time(15, 20) and now.time() < dt_time(15, 30)

    def _daily_reset_worker(self):
        """매일 자정에 일일 작업 완료 플래그를 리셋합니다."""
        while not self.shutdown_event.is_set():
            now = datetime.now()
            if now.time() >= dt_time(0, 0) and now.time() < dt_time(0, 1):
                if self.sell_worker_done_today or self.buy_worker_done_today:
                    logger.info("[SYSTEM] 자정 리셋: 일일 작업 플래그를 초기화합니다.")
                    self.sell_worker_done_today = False
                    self.buy_worker_done_today = False
            time.sleep(60) # 1분마다 체크

    # --- 신규 워커: 매도, 스크리닝, 매수 --- #

    def _opening_sell_worker(self):
        """익일 시초가 매도 로직 (09:00 ~ 09:30) - 트레일링 스탑 적용"""
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_sell_time(now) and not self.sell_worker_done_today:
                    # --- 매도 로직 초기화 ---
                    if not self.positions_to_sell:
                        self.positions_to_sell = dict(self.position_manager.positions.items())
                        if not self.positions_to_sell:
                            logger.info("[SELL_WORKER] 매도할 보유 종목이 없습니다.")
                            self.sell_worker_done_today = True
                            continue
                        
                        logger.info(f"[SELL_WORKER] 시초가 매도 로직 시작. 대상: {len(self.positions_to_sell)}개")
                        # 시가 및 초기 피크가 설정
                        for code, position in self.positions_to_sell.items():
                            # TODO: 시가를 market_cache에서 가져와야 함
                            open_price = self.market_cache.get_quote(code) # 임시
                            if open_price:
                                self.sell_open_prices[code] = open_price
                                self.sell_peaks[code] = max(position.get('avg_price', open_price), open_price)
                            else: # 시가 조회가 안될 경우, 매수 평균가를 기준으로 설정
                                self.sell_open_prices[code] = position.get('avg_price', 0)
                                self.sell_peaks[code] = position.get('avg_price', 0)

                    # --- 실시간 매도 조건 확인 루프 ---
                    positions_to_check = list(self.positions_to_sell.keys())
                    for code in positions_to_check:
                        current_price = self.market_cache.get_quote(code)
                        if current_price:
                            self._check_sell_conditions(code, current_price)
                
                # --- 09:30 강제 청산 ---
                if now.time() >= dt_time(9, 30) and not self.sell_worker_done_today:
                    logger.warning("[SELL_WORKER] 09:30 도달, 미청산 종목 강제 매도")
                    remaining_positions = list(self.positions_to_sell.keys())
                    for code in remaining_positions:
                        self._execute_sell(code, "Forced Liquidation")
                    
                    if not self.positions_to_sell:
                        summary_text = trade_summary.get_morning_sell_summary()
                        notifier.send_message(summary_text)
                        self.sell_worker_done_today = True
                        logger.info("[SELL_WORKER] 시초가 매도 및 요약 전송 로직 완료")

                time.sleep(2) # 2초마다 확인
            except Exception as e:
                logger.error(f"[SELL_WORKER] 오류: {e}", exc_info=True)
                time.sleep(60)

    def _check_sell_conditions(self, code: str, current_price: float):
        """gemini.md에 명시된 두 가지 매도 조건을 확인하고 매도를 실행합니다."""
        position = self.positions_to_sell[code]
        avg_price = position.get('avg_price', 0)
        if avg_price == 0: return

        # 피크 가격 업데이트
        self.sell_peaks[code] = max(self.sell_peaks.get(code, 0), current_price)
        peak_price = self.sell_peaks[code]

        profit = (current_price / avg_price) - 1
        
        # 조건 (A): 이익 실현 트레일링 스탑
        min_profit_pct = self.config.get('trading', {}).get('min_profit_pct_sell', 0.002)
        trail_drop_pct = self.config.get('trading', {}).get('trail_drop_pct_sell', 0.006)
        if profit >= min_profit_pct and (peak_price / current_price - 1) >= trail_drop_pct:
            self._execute_sell(code, f"Trailing Stop (수익률: {profit:.2%})")
            return

        # 조건 (B): 시초가 대비 하락 손절
        open_price = self.sell_open_prices.get(code, 0)
        if open_price > 0:
            open_fail_drop_ratio = self.config.get('trading', {}).get('open_fail_drop_ratio', 0.985)
            if profit < min_profit_pct and current_price < (open_price * open_fail_drop_ratio):
                self._execute_sell(code, f"Open Fail Stop (시가대비: {(current_price/open_price-1):.2%})")
                return

    def _execute_sell(self, code: str, reason: str):
        """실제 매도 주문을 실행하고 후속 처리를 담당합니다."""
        if code not in self.positions_to_sell:
            return

        position = self.positions_to_sell[code]
        shares = int(position['shares'])
        logger.info(f"[SELL] 매도 조건 충족: {position['name']} ({code}) - 사유: {reason}")
        
        result = self.account_manager.place_sell_order_market(code, shares)
        if result and result.get('success'):
            # 체결가는 API 응답 또는 실시간 체결 데이터로 받는 것이 가장 정확
            # 여기서는 임시로 현재가를 사용
            current_price = self.market_cache.get_quote(code) or position.get('avg_price', 0)
            
            # PositionManager를 통해 포지션 종료 및 거래 기록
            self.position_manager.close_position(
                code=code,
                quantity=shares,
                price=current_price,
                reason=reason,
                name=position['name']
            )
            logger.info(f"[SELL] 시장가 매도 주문 완료 및 포지션 종료: {position['name']} ({code}) {shares}주")
            
            # 매도 대상 목록에서 제거
            del self.positions_to_sell[code]
        else:
            logger.error(f"[SELL] 매도 주문 실패: {position['name']} ({code})")

    def _closing_price_screening_worker(self):
        """장중 후보군 스크리닝 (09:30 ~ 15:20)"""
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_screening_time(now):
                    logger.info("[SCREENER] 종가 매수 후보군 스크리닝 시작...")
                    volume_stocks = self.account_manager.get_volume_ranking(count=100)
                    logger.info(f"[SCREENER] API 조회 결과: 거래량 상위 {len(volume_stocks)}개 종목 수신")
                    if not volume_stocks:
                        time.sleep(60)
                        continue

                    self.closing_price_candidates = closing_price_stock_filter(
                        self.market_cache, volume_stocks, self.account_manager.api
                    )

                    # Fallback 로직: 필터링된 후보가 없으면 거래량 상위 종목으로 대체
                    if not self.closing_price_candidates and volume_stocks:
                        logger.warning("[SCREENER] 필터링된 후보가 없어 거래량 상위 종목으로 Fallback합니다.")
                        
                        from strategies.closing_price_trader import EXCLUDE_KEYWORDS

                        fallback_candidates = []
                        for stock in volume_stocks:
                            stock_name = stock.get('name', '')
                            # 제외 키워드가 포함된 종목은 건너뛰기 (대소문자 무시)
                            if any(keyword.upper() in stock_name.upper() for keyword in EXCLUDE_KEYWORDS):
                                continue
                            
                            fallback_candidates.append({
                                'code': stock.get('code'),
                                'name': stock_name,
                                'turnover': stock.get('turnover', 0),
                                'total_score': 0.0,
                                'scores': {},
                                'reason': 'fallback_volume'
                            })
                            if len(fallback_candidates) >= 5:
                                break  # 5개 채우면 중단
                        
                        self.closing_price_candidates = fallback_candidates

                    logger.info(f"[SCREENER] 후보군 업데이트 완료: {len(self.closing_price_candidates)}개")

                    if self.closing_price_candidates:
                        # Log and notify top 5 candidates
                        top_n = 5
                        message_lines = ["[종가매매 후보 업데이트]"]
                        for i, stock in enumerate(self.closing_price_candidates[:top_n]):
                            reason = f" ({stock['reason']})" if 'reason' in stock else ""
                            score_display = f"점수: {stock['total_score']:.1f}" if stock['total_score'] > 0 else "Fallback"
                            line = f"{i+1}. {stock['name']} ({stock['code']}) - {score_display}{reason}"
                            message_lines.append(line)
                        
                        full_message = "\n".join(message_lines)
                        logger.info(full_message)
                        notifier.send_message(full_message)
                    
                    # 후보군에 대한 실시간 시세 구독 관리
                    new_codes = {self._normalize_code(c['code']) for c in self.closing_price_candidates}
                    self._update_subscriptions(new_codes)

                time.sleep(300) # 5분마다 스크리닝
            except Exception as e:
                logger.error(f"[SCREENER] 오류: {e}", exc_info=True)
                time.sleep(300)

    def _closing_price_buy_worker(self):
        """종가 매수 로직 (15:20 ~ 15:30), 후보군 부족 시 예비 후보군에서 보충"""
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                if self._is_buy_time(now) and not self.buy_worker_done_today:
                    logger.info("[BUY_WORKER] 종가 매수 로직 시작")
                    
                    primary_candidates = self.closing_price_candidates[:5]
                    final_buy_list = primary_candidates
                    num_primary = len(primary_candidates)

                    if num_primary < 5:
                        needed = 5 - num_primary
                        logger.info(f"[BUY_WORKER] 실시간 후보군이 {num_primary}개 이므로, 예비 후보군에서 {needed}개를 보충합니다.")
                        
                        try:
                            fallback_df = code_loader(top_n=10) # 예비 후보 10개 로드
                            if not fallback_df.empty:
                                primary_codes = {c['code'] for c in primary_candidates}
                                
                                # 예비 후보에서 중복 제거
                                fallback_df = fallback_df[~fallback_df['종목코드'].isin(primary_codes)]
                                
                                # 부족한 만큼 예비후보에서 추가
                                fallback_candidates_to_add = fallback_df.head(needed)
                                
                                for _, row in fallback_candidates_to_add.iterrows():
                                    # 포맷을 primary_candidates와 동일하게 맞춤
                                    final_buy_list.append({
                                        'code': row['종목코드'],
                                        'name': row['종목명'],
                                        'reason': 'fallback' # 보충된 종목임을 표시
                                    })
                                logger.info(f"[BUY_WORKER] 예비 후보군에서 {len(fallback_candidates_to_add)}개 보충 완료.")
                            else:
                                logger.warning("[BUY_WORKER] 예비 후보군을 불러왔으나 비어있습니다.")
                        except Exception as e:
                            logger.error(f"[BUY_WORKER] 예비 후보군 처리 중 오류: {e}", exc_info=True)

                    if not final_buy_list:
                        logger.warning("[BUY_WORKER] 최종 매수 후보군이 없습니다. 매수를 건너뜁니다.")
                    else:
                        logger.info("[BUY_WORKER] 매수 실행 직전, 최신 계좌 잔고를 조회합니다...")
                        cash_balance = self.account_manager.get_simple_balance()
                        logger.info(f"[BUY_WORKER] 조회된 주문 가능 현금: {cash_balance:,.0f}원")

                        if cash_balance < 10000: # 만원 미만일 경우 매수 절차 건너뛰기
                            logger.warning(f"[BUY_WORKER] 주문 가능 현금이 {cash_balance:,.0f}원으로 너무 적어 매수를 건너뜁니다.")
                            self.buy_worker_done_today = True
                            continue

                        budget_per_stock = cash_balance / len(final_buy_list)
                        logger.info(f"[BUY_WORKER] 최종 {len(final_buy_list)}개 종목 매수 시작. 종목당 예산: {budget_per_stock:,.0f}원")

                        for stock in final_buy_list:
                            code = stock['code']
                            # API 호출 최소화를 위해 현재가는 매수 직전에만 조회
                            price_info = self.account_manager.get_stock_price(code)
                            current_price = float(price_info.get('stck_prpr', 0))
                            if current_price > 0:
                                shares = int(budget_per_stock // current_price)
                                if shares > 0:
                                    self.account_manager.place_buy_order_market(code, shares)
                                    logger.info(f"[BUY] 시장가 매수 주문: {stock['name']} ({code}) {shares}주")
                                    time.sleep(0.5) # 주문 API 과부하 방지
                        
                        buy_names = [s['name'] for s in final_buy_list]
                        notifier.send_message(f"종가 매수 완료: {', '.join(buy_names)}")

                    self.buy_worker_done_today = True
                    logger.info("[BUY_WORKER] 종가 매수 로직 완료")
                time.sleep(10)
            except Exception as e:
                logger.error(f"[BUY_WORKER] 오류: {e}", exc_info=True)
                time.sleep(60)

    def _update_subscriptions(self, new_codes: Set[str]):
        """현재 구독 중인 종목과 새로운 후보군을 비교하여 구독을 업데이트합니다."""
        if not self.ws_manager or not self.ws_manager.is_connected:
            logger.warning("[SUB_MGR] 웹소켓이 연결되지 않아 구독을 업데이트할 수 없습니다.")
            return

        # 보유 종목은 항상 구독 유지
        owned_codes = set(self.position_manager.positions.keys())
        required_codes = new_codes.union(owned_codes)

        codes_to_add = required_codes - self.subscribed_codes
        codes_to_remove = self.subscribed_codes - required_codes

        if codes_to_add:
            logger.info(f"[SUB_MGR] 신규 구독 추가: {list(codes_to_add)}")
            for code in codes_to_add:
                self.ws_manager.subscribe(code)
        
        if codes_to_remove:
            logger.info(f"[SUB_MGR] 기존 구독 해지: {list(codes_to_remove)}")
            for code in codes_to_remove:
                self.ws_manager.unsubscribe(code)
        
        # self.subscribed_codes는 ws_manager에서 관리되지만, 명시적으로 동기화
        self.subscribed_codes = required_codes

    # --- 기존 유틸리티 메서드 (일부 유지) --- #
    def _wait_and_connect_ws(self) -> bool:
        # ... (기존과 동일) ...
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
            trade_summary.print_shutdown_summary()
            notifier.send_message(f"시스템 종료\n\n{trade_summary.get_summary_text()}")

    def _signal_handler(self, signum, frame):
        self.shutdown()

    def print_summary(self, date_str: Optional[str] = None):
        # ... (기존과 동일) ...
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
