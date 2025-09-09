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
from strategies.stock_screener import scalping_stock_filter
from strategies.wave_scalper import WaveScalper
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
    """통합 거래 시스템 - 웹소켓 기반"""
    
    def __init__(self, system_config: Dict):
        self.config = system_config
        self.shutdown_event = threading.Event()
        self.account_manager = None
        self.position_manager = RealPositionManager()
        self.balance_manager = BalanceManager()
        self.ws_manager: KISWebSocketClient = None
        self.recently_sold: Dict[str, float] = {} # {code: timestamp}
        self.subscribed_codes: Set[str] = set()
        self.beginning_total_assets = 0
        self.portfolio_peak_profit_rate = 0.0
        self.trailing_profit_taking_active = False
        self.is_buy_stopped = False
        self.stop_buy_reason = ""
        self.main_strategy_candidates: Set[str] = set()

        self.wave_scalpers: Dict[str, WaveScalper] = {}
        self.wave_scalper_params = {
            'window_secs': 240,
            'recalc_secs': 30,
            'enter_band': 0.12,     # 시작값 (적응형으로 덮어쓰기 권장)
            'exit_band': 0.10,
            'atr_period': 20,
            'breakout_k': 1.2,      # 가짜돌파 감소
            'vol_spike_k': 2.0,     # 저밴드에서만 강제
            'cooldown_secs': 40,    # 과매매 방지
            'max_positions': 1,
            'position_size_krw': 100000,
            'stop_loss_pct': -0.8,  # 시작값 (적응형으로 덮어쓰기 권장)
            'take_profit_pct': 0.9, # 시작값 (적응형으로 덮어쓰기 권장)
            'fee_pct_roundtrip': 0.0008,
            'min_data_points': 120,
            'is_buy_stopped_ref': lambda: self.is_buy_stopped,

            # Box-range detection enhancements
            'box_min_bounces': 2,           # 박스권으로 판단하기 위한 최소 상/하단 터치 횟수
            'box_rejection_spike_pct': 1.5, # N초 내 지정된 % 이상 급등/락 시 박스권 판단 보류

            # Boot mode params
            'boot_duration_secs': 180,       # 부트 모드 유지 시간(초) = 3분
            'boot_min_points': 30,           # 부트 채널 최소 샘플 수
            'disable_vol_spike_secs': 120,   # 오픈 직후 거래량 스파이크 필터 비활성(초)
            'boot_enter_band': 0.10,         # 부트 모드 밴드 (엔트리)
            'boot_exit_band': 0.10,          # 부트 모드 밴드 (엑싯)
        }

        signal.signal(signal.SIGINT, self._signal_handler)
        self.market_cache = None # initialize에서 생성
        logger.info("[SYSTEM] 웹소켓 기반 거래 시스템으로 초기화")

    def _normalize_code(self, code: str) -> str:
        """코드를 'A' + 6자리 숫자로 정규화합니다."""
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

            # MarketCache 초기화 (AccountManager가 생성된 후)
            self.market_cache = init_market_cache(self.config, self.position_manager, self.account_manager)

            # 오늘 날짜의 market_events.json 파일 경로 생성
            today_date_str = datetime.now().strftime("%Y-%m-%d")
            market_events_file = f"data/market_events_{today_date_str}.json"

            # 과거 틱 데이터 로드
            self.market_cache.load_historical_data(market_events_file)

            # 과거 1분봉 데이터 로드
            self.market_cache.load_historical_candles("data/historical_ohlcv_1min.json")

            logger.info("... [SYSTEM] 실시간 계좌 잔고 조회 시도...")
            cash_balance = self.account_manager.get_simple_balance()
            if cash_balance <= 0:
                logger.warning("[SYSTEM] API를 통한 실시간 잔고 조회에 실패했거나 잔고가 0입니다. 내부 잔고 관리자가 부정확할 수 있습니다.")
                # 기존 파일에 저장된 잔고를 사용하도록 유도
                cash_balance = self.balance_manager.get_balance()
                logger.info(f"[SYSTEM] 파일에서 로드한 기존 잔고를 사용합니다: {cash_balance:,}원")
            else:
                # 성공 시에만 잔고 관리자 업데이트
                self.balance_manager.set_balance(cash_balance)
            current_positions = self.account_manager.get_current_positions()
            stock_balance = sum(int(p.get('evlu_amt', 0)) for p in current_positions)
            self.beginning_total_assets = cash_balance + stock_balance
            trade_summary.set_starting_balance(self.beginning_total_assets) # 시작 잔고 설정 (총자산 기준)
            logger.info(f"[SYSTEM] 시작 총자산: {self.beginning_total_assets:,}원 (현금 {cash_balance:,} + 주식 {stock_balance:,})")

            position_codes = set()
            if current_positions:
                logger.info(f"[SYSTEM] {len(current_positions)}개 보유 종목 발견")
                for pos in current_positions:
                    code = pos.get('pdno')
                    if code:
                        normalized_code = self._normalize_code(code)
                        self.position_manager.add_position(normalized_code, int(pos.get('hldg_qty')), float(pos.get('pchs_avg_pric')), pos.get('prdt_name'))
                        position_codes.add(normalized_code)
                logger.info(f"[SYSTEM] 보유 종목 포지션 복원 완료: {list(position_codes)}")

            # KIS API는 보통 40~50개의 실시간 구독 제한이 있습니다. 안전하게 40개로 설정.
            MAX_SUBSCRIPTIONS = self.config.get('system', {}).get('max_subscriptions', 40)

            # 보유 종목을 우선적으로 구독 리스트에 포함
            codes_to_subscribe = set(position_codes)
            
            # 만약 보유 종목만으로도 최대치를 넘는다면, 경고 후 일부만 구독
            if len(codes_to_subscribe) > MAX_SUBSCRIPTIONS:
                logger.warning(f"보유 종목({len(codes_to_subscribe)}개)이 최대 구독 가능 개수({MAX_SUBSCRIPTIONS}개)를 초과합니다. 일부만 구독합니다.")
                codes_to_subscribe = set(list(codes_to_subscribe)[:MAX_SUBSCRIPTIONS])

            # 남은 슬롯만큼 code_loader에서 가져온 종목으로 채움
            remaining_slots = MAX_SUBSCRIPTIONS - len(codes_to_subscribe)
            if remaining_slots > 0:
                initial_stocks_df = code_loader(top_n=MAX_SUBSCRIPTIONS) # 넉넉하게 가져옴
                initial_codes = {self._normalize_code(c) for c in initial_stocks_df['종목코드'].tolist()} if not initial_stocks_df.empty else set()
                new_codes_to_add = [code for code in initial_codes if code not in codes_to_subscribe]
                codes_to_subscribe.update(new_codes_to_add[:remaining_slots])
            
            approval_key = self.account_manager.api.get_approval_key()
            if not approval_key: raise Exception("웹소켓 승인 키 발급 실패")

            self.ws_manager = KISWebSocketClient(config=self.config, account_manager=self.account_manager, approval_key=approval_key, codes=codes_to_subscribe, market_cache=self.market_cache)
            self.subscribed_codes.update(codes_to_subscribe)
            # 웹소켓은 run() 단계에서 장 시작 직전에 연결됩니다.
            logger.info(f"[SYSTEM] 시스템 초기화 완료. 총 {len(self.subscribed_codes)}개 종목 구독 준비 완료.")
            return True
            
        except Exception as e:
            logger.error(f"[SYSTEM] 초기화 실패: {e}")
            logger.error(traceback.format_exc())
            return False

    def run(self):
        if not self.initialize():
            self.shutdown()
            return False

        min_balance = 100000
        if self.beginning_total_assets < min_balance:
            logger.error(f"[SYSTEM] 시작 총자산 부족 ({self.beginning_total_assets:,}원). 최소 필요 금액: {min_balance:,}원")
            self.shutdown()
            return False

        # 장 시작 시간에 맞춰 웹소켓 연결
        if not self._wait_and_connect_ws():
            logger.error("[SYSTEM] 웹소켓 연결에 실패하여 시스템을 종료합니다.")
            self.shutdown()
            return False

        logger.info("[SYSTEM] 실거래 시스템 실행 시작")
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
        threading.Thread(target=self._screening_worker, daemon=True).start()
        threading.Thread(target=self._sell_decision_worker, daemon=True).start()
        threading.Thread(target=self._monitoring_worker, daemon=True).start()
        threading.Thread(target=self._wave_scalping_worker, daemon=True).start()
        logger.info("[WORKER] 모든 워커 시작 완료")

    def _wait_and_connect_ws(self) -> bool:
        """장 시작 시간에 맞춰 웹소켓에 연결합니다."""
        logger.info("[SYSTEM] 장 시작(09:00)까지 대기하며, 08:58에 웹소켓 연결을 시도합니다.")
        while not self.shutdown_event.is_set():
            now = datetime.now()
            # 평일이고, 8시 58분 이후인가?
            if now.weekday() < 5 and now.time() >= dt_time(8, 58):
                logger.info("[SYSTEM] 장 시작 시간이 임박하여 웹소켓 연결을 시작합니다.")
                try:
                    self.ws_manager.start()
                    if not self.ws_manager.wait_for_connection(timeout=15):
                        raise Exception("웹소켓 연결 시간 초과")
                    logger.info("[SYSTEM] 웹소켓 연결 성공.")
                    return True # 연결 성공
                except Exception as e:
                    logger.error(f"[SYSTEM] 장 시작 전 웹소켓 연결 실패: {e}")
                    logger.error(traceback.format_exc())
                    return False # 연결 실패
            
            # 아직 시간이 아니면 10초 대기
            time.sleep(10)
        
        logger.info("[SYSTEM] 웹소켓 연결 대기 중 시스템 종료 신호 수신.")
        return False

    def _is_market_hours(self) -> bool:
        now = datetime.now().time()
        return dt_time(9, 0) <= now <= dt_time(15, 20)

    def _screening_worker(self):
        REBUY_COOLDOWN_SEC = 300 # 5분
        initial_wait_done = False
        while not self.shutdown_event.is_set():
            try:
                if not initial_wait_done and self._is_market_hours():
                    trading_config = self.config.get('trading', {})
                    boot_mode_enabled = trading_config.get('enable_boot_mode_trading', False)

                    if not boot_mode_enabled:
                        wait_minutes = trading_config.get('initial_data_wait_min', 10)
                        logger.info(f"[SCREENER] 초기 데이터 축적을 위해 {wait_minutes}분 대기합니다...")
                        time.sleep(wait_minutes * 60)
                    else:
                        logger.info("[SCREENER] 부트 모드가 활성화되어, 장 시작 즉시 스크리닝을 시작합니다.")
                    
                    initial_wait_done = True

                # 주기적으로 최근 매도 목록 정리 (쿨다운 만료)
                now = time.time()
                expired_sold = [code for code, ts in self.recently_sold.items() if now - ts > REBUY_COOLDOWN_SEC]
                if expired_sold:
                    logger.debug(f"[GC] 재매수 쿨다운 해제: {expired_sold}")
                    for code in expired_sold:
                        del self.recently_sold[code]

                if self._is_market_hours():
                    logger.info("[SCREENER] 신규 종목 탐색 및 구독 관리 시작...")
                    volume_stocks = self.account_manager.get_volume_ranking(count=100)
                    if not volume_stocks:
                        time.sleep(60)
                        continue

                    # 1. 지능형 구독 관리 (안정화 버전)
                    MAX_SUBSCRIPTIONS = self.config.get('system', {}).get('max_subscriptions', 40)
                    
                    # Define priority codes (all normalized)
                    held_codes = set(self.position_manager.positions.keys()) # Already normalized from initialization
                    wave_scalper_held_codes = {self._normalize_code(code) for code, s in self.wave_scalpers.items() if s.position}
                    all_held_codes = held_codes.union(wave_scalper_held_codes)

                    candidate_codes = {self._normalize_code(c['code']) for c in scalping_stock_filter(self.market_cache, volume_stocks, self.account_manager.api)}
                    self.main_strategy_candidates = candidate_codes
                    
                    # Build the desired subscription list
                    desired_codes = all_held_codes.copy()
                    for code in candidate_codes:
                        if len(desired_codes) >= MAX_SUBSCRIPTIONS:
                            break
                        if code not in desired_codes:
                            desired_codes.add(code)

                    # Compare and update
                    codes_to_add = desired_codes - self.subscribed_codes
                    codes_to_remove = self.subscribed_codes - desired_codes

                    if codes_to_remove:
                        logger.info(f"[SUB] 구독 해지 목록: {list(codes_to_remove)}")
                        for code in codes_to_remove:
                            if code in all_held_codes: continue # Safeguard
                            logger.info(f"[SUB] 구독 해지 (후보 변경): {code}")
                            normalized_code = self._normalize_code(code) # Ensure normalized for unsubscribe
                            self.ws_manager.unsubscribe(normalized_code)
                            self.subscribed_codes.discard(normalized_code)
                            time.sleep(0.25) # Prevent flooding

                    if codes_to_add:
                        logger.info(f"[SUB] 신규 구독 목록: {list(codes_to_add)}")
                        for code in codes_to_add:
                            if len(self.subscribed_codes) >= MAX_SUBSCRIPTIONS:
                                logger.warning("[SUB] 최대 구독 개수에 도달하여 추가 구독 불가.")
                                break
                            logger.info(f"[SUB] 신규 구독 추가 (후보): {code}")
                            normalized_code = self._normalize_code(code) # Ensure normalized for subscribe
                            self.ws_manager.subscribe(normalized_code)
                            self.subscribed_codes.add(normalized_code)
                            time.sleep(0.25) # Prevent flooding

                    # 2. 매수 처리 (기본 스캘핑)
                    buyable_candidates = [c for c in volume_stocks if self._normalize_code(c['code']) in candidate_codes]
                    logger.info(f"[SCREENER] 최종 매수 후보: {len(buyable_candidates)}개")
                    self._process_buy(buyable_candidates)

                time.sleep(60)
            except Exception as e:
                logger.error(f"[SCREENER] 스크리닝 워커 오류: {e}")
                logger.error(traceback.format_exc())
                time.sleep(60)

    def _wave_scalping_worker(self):
        while not self.shutdown_event.is_set():
            try:
                if not self._is_market_hours():
                    time.sleep(5)
                    continue

                for code in list(self.subscribed_codes):
                    if code in self.position_manager.positions: # 기본 전략이 관리하는 포지션은 건너뜀
                        continue

                    # 기본 전략 후보군이라도 wave_scalper 진입 허용 (기본 전략이 진입 안했을 수 있으므로)
                    # if code in self.main_strategy_candidates: # 기본 전략의 후보 종목은 건너뜀
                    #     continue

                    price_data = self.market_cache.get_quote_full(f"A{code.lstrip('A')}")
                    if not (price_data and price_data.get('price')):
                        continue
                    
                    tick = {
                        'timestamp': time.time(),
                        'price': float(price_data.get('price')),
                        'volume': float(price_data.get('volume', 0)),
                        'code': code
                    }

                    # Dynamic position sizing for wave scalper
                    trading_config = self.config.get('trading', {})
                    sizing_method = trading_config.get('position_sizing_method', 'fixed')
                    
                    wave_buy_amount = self.wave_scalper_params.get('position_size_krw', 100000) # default
                    if sizing_method == 'dynamic':
                        # 총자산 대비 비율로 1회 매수 예산 결정 (웨이브 스캘퍼는 더 작게)
                        wave_per_trade_ratio = trading_config.get('wave_per_trade_ratio', 0.025) # 기본 2.5%
                        trade_budget = self.beginning_total_assets * wave_per_trade_ratio

                        # 가용 현금과 비교하여 보수적으로 결정
                        cash_balance = self.balance_manager.get_balance()
                        wave_buy_amount = min(trade_budget, cash_balance * 0.95)
                    
                    logger.info(f"[WAVE_DEBUG] Sizing Method: '{sizing_method}'")
                    if sizing_method == 'dynamic':
                        logger.info(f"[WAVE_DEBUG] Total Assets: {self.beginning_total_assets:,.0f}, Cash: {cash_balance:,.0f}, Ratio: {wave_per_trade_ratio:.2%}")
                    logger.info(f"[WAVE_DEBUG] Calculated budget before clipping: {wave_buy_amount:,.0f} KRW")

                    min_buy = trading_config.get('min_position_krw', 50000)
                    max_buy = trading_config.get('max_position_krw', 1000000)
                    tick['buy_amount'] = np.clip(wave_buy_amount, min_buy, max_buy)

                    logger.info(f"[WAVE_DEBUG] Budget after clipping ({min_buy:,.0f} ~ {max_buy:,.0f}): {tick['buy_amount']:,.0f} KRW")

                    if code not in self.wave_scalpers:
                        self.wave_scalpers[code] = WaveScalper(code, self.account_manager, self.wave_scalper_params)
                    
                    scalper = self.wave_scalpers[code]
                    scalper.on_tick(tick)

                time.sleep(2)
            except Exception as e:
                logger.error(f"[WAVE_SCALPER_WORKER] Error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(30)

    def _sell_decision_worker(self):
        eod_cleanup_done = False
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                # 장 마감(15:20) 전에는 개별 매도 로직 수행
                if self._is_market_hours() and self.position_manager.positions:
                    self._process_sell_positions()
                
                # 장 마감(15:20) 이후, 한 번만 일괄 청산 수행
                if now.time() >= dt_time(15, 20) and self.position_manager.positions and not eod_cleanup_done:
                    logger.info("[SYSTEM] 장 마감 시간 도달. 모든 포지션 일괄 청산을 시작합니다.")
                    self._sell_all_positions("장 마감 일괄 청산")
                    eod_cleanup_done = True # 하루에 한 번만 실행되도록 플래그 설정

                # 다음 날을 위해 자정이 지나면 플래그 리셋
                if now.time() < dt_time(1, 0): # 새벽 1시 이전에 리셋
                    eod_cleanup_done = False

                time.sleep(5)
            except Exception as e:
                logger.error(f"[SELL] 매도 결정 워커 오류: {e}")
                time.sleep(30)

    def _sell_all_positions(self, reason: str):
        logger.info(f"전체 포지션 매도 시작. 사유: {reason}")
        # 기본 포지션 정리
        positions_to_sell = list(self.position_manager.positions.items())
        for code, position in positions_to_sell:
            try:
                shares_to_sell = int(position['shares'])
                logger.info(f"[SELL ALL] 시장가 매도 주문 시도: {position['name']} ({code}) {shares_to_sell}주")
                result = self.account_manager.place_sell_order_market(code, shares_to_sell)
                if result and result.get('success'):
                    self.recently_sold[code] = time.time()
                    current_price = 0
                    price_info = self.account_manager.get_stock_price(code)
                    if price_info and price_info.get('stck_prpr'):
                        current_price = float(price_info.get('stck_prpr'))

                    self.position_manager.close_position(
                        code=code,
                        quantity=shares_to_sell,
                        price=current_price,
                        reason=reason,
                        name=position['name']
                    )
                    self.ws_manager.unsubscribe(code)
                    self.subscribed_codes.discard(code)
                    self._sync_balance()
                    buy_price = float(position['price'])
                    pnl = (current_price - buy_price) * shares_to_sell if current_price > 0 else 0
                    profit_rate = ((current_price / buy_price) - 1) * 100 if buy_price > 0 and current_price > 0 else 0
                    msg = (
                        f"장마감매도: {position['name']} ({code})\n"
                        f"- 수익률: {profit_rate:+.2f}%\n"
                        f"- 실현손익: {pnl:+,}원"
                    )
                    logger.info(msg)
                    notifier.send_message(msg)
                else:
                    error_msg = (result or {}).get('error', 'Unknown')
                    logger.error(f"[SELL ALL] 매도 주문 실패: {position['name']} ({code}) - 사유: {error_msg}")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"[SELL ALL] 개별 종목 매도 중 오류: {position.get('name', code)} - {e}")
        
        # 웨이브 스캘퍼 포지션 정리
        for code, scalper in self.wave_scalpers.items():
            if scalper.position:
                logger.info(f"[WAVE_SCALPER] 장 마감, {code} 포지션 정리")
                price_info = self.account_manager.get_stock_price(code)
                if price_info and price_info.get('stck_prpr'):
                    last_tick = {'price': float(price_info.get('stck_prpr')), 'code': code, 'timestamp': time.time()}
                    scalper.try_sell(last_tick, reason="EOD_cleanup")

        logger.info("전체 포지션 매도 완료.")

    def _monitoring_worker(self):
        """10초마다 시스템의 현재 상태와 포트폴리오 수익률을 모니터링하고 리스크 규칙을 적용합니다."""
        while not self.shutdown_event.is_set():
            try:
                # 기본 모니터링
                pos_count = len(self.position_manager.positions)
                sub_count = len(self.subscribed_codes)
                logger.info(f"[MONITOR] 운영중 - 보유: {pos_count}개, 구독: {sub_count}개")

                # --- 포트폴리오 리스크 관리 로직 ---
                now = datetime.now()
                if not self._is_market_hours() or self.beginning_total_assets == 0:
                    time.sleep(10)
                    continue

                # 장 초반 5분간은 포트폴리오 전체 손익 로직을 적용하지 않음
                if now.time() < dt_time(9, 5):
                    logger.info("[PNL_MONITOR] 장 초반 5분간 포트폴리오 PNL 모니터링을 보류합니다.")
                    time.sleep(10)
                    continue

                # 1. 현재 총자산 계산
                current_cash = self.balance_manager.get_balance()
                stock_eval_balance = 0
                # 1. 기본 전략 포지션 가치 계산
                for code, position in self.position_manager.positions.items():
                    normalized_code = f"A{code.lstrip('A')}"
                    price_data = self.market_cache.get_quote_full(normalized_code)
                    current_price = 0
                    if price_data and price_data.get('price'):
                        current_price = float(price_data.get('price'))
                    else:
                        price_info = self.account_manager.get_stock_price(code)
                        if price_info and price_info.get('stck_prpr'):
                            current_price = float(price_info.get('stck_prpr'))
                    
                    if current_price > 0:
                        stock_eval_balance += current_price * int(position['shares'])
                    else:
                        stock_eval_balance += float(position['price']) * int(position['shares'])

                # 2. 웨이브 스캘퍼 포지션 가치 계산
                for code, scalper in self.wave_scalpers.items():
                    if scalper.position:
                        normalized_code = f"A{code.lstrip('A')}"
                        price_data = self.market_cache.get_quote_full(normalized_code)
                        current_price = 0
                        if price_data and price_data.get('price'):
                            current_price = float(price_data.get('price'))
                        else:
                            price_info = self.account_manager.get_stock_price(code)
                            if price_info and price_info.get('stck_prpr'):
                                current_price = float(price_info.get('stck_prpr'))

                        if current_price > 0:
                            stock_eval_balance += current_price * int(scalper.position['qty'])
                        else:
                            stock_eval_balance += float(scalper.position['avg_price']) * int(scalper.position['qty'])
                
                current_total_assets = current_cash + stock_eval_balance

                # 2. 수익률 계산
                profit_rate = (current_total_assets / self.beginning_total_assets) - 1
                
                logger.info(f"[PNL_MONITOR] 현재 총자산: {current_total_assets:,.0f}원 | 시작 자산: {self.beginning_total_assets:,.0f}원 | 수익률: {profit_rate:+.2%}")

                # 3. 자동 종료 규칙 확인
                shutdown_reason = ""
                # 규칙 1: -3% 손실 시 강제 종료
                if profit_rate <= -0.03:
                    shutdown_reason = f"전체 포트폴리오 손실률 -3% 도달 (현재: {profit_rate:+.2%})"
                
                # 규칙 2: +5% 수익 시 강제 종료
                elif profit_rate >= 0.05:
                    shutdown_reason = f"전체 포트폴리오 수익률 +5% 도달 (현재: {profit_rate:+.2%})"

                # 규칙 3: +3% 이상에서 수익 보존 모드 (Trailing)
                else:
                    # 수익 보존 모드 활성화
                    if not self.trailing_profit_taking_active and profit_rate >= 0.03:
                        self.trailing_profit_taking_active = True
                        self.portfolio_peak_profit_rate = profit_rate
                        msg = f"[PNL_MONITOR] 수익 보존 모드 활성화! 현재 수익률: {profit_rate:+.2%}"
                        logger.info(msg)
                        notifier.send_message(msg)

                    # 활성화된 경우, 최고 수익률 대비 하락 감시
                    if self.trailing_profit_taking_active:
                        self.portfolio_peak_profit_rate = max(self.portfolio_peak_profit_rate, profit_rate)
                        # 최고점 대비 0.5% 이상 하락 시 종료
                        drawdown_from_peak = self.portfolio_peak_profit_rate - profit_rate
                        if drawdown_from_peak >= 0.005:
                            shutdown_reason = (
                                f"수익 보존 모드 종료! "
                                f"최고 수익률 {self.portfolio_peak_profit_rate:+.2%} 대비 하락 "
                                f"(현재: {profit_rate:+.2%})"
                            )

                if shutdown_reason and not self.is_buy_stopped:
                    self.is_buy_stopped = True
                    self.stop_buy_reason = shutdown_reason
                    msg = f"🚨 [BUY STOP] 신규 매수 중단: {shutdown_reason}"
                    logger.warning(msg)
                    notifier.send_message(msg)

                time.sleep(10)
            except Exception as e:
                logger.error(f"[MONITOR] 모니터링 워커 오류: {e}")
                logger.error(traceback.format_exc())
                time.sleep(30)

    def _sync_balance(self):
        """API를 통해 실제 계좌 잔고를 조회하고 내부 잔고 관리자를 동기화합니다."""
        try:
            logger.info("[SYNC] API를 통해 잔고 동기화를 시작합니다.")
            # API 호출에 약간의 지연 시간을 두어 체결 후 정산이 반영될 시간을 줍니다.
            time.sleep(2) 
            
            actual_cash = self.account_manager.get_simple_balance()
            if actual_cash > 0:
                self.balance_manager.set_balance(actual_cash)
                logger.info(f"[SYNC] 잔고 동기화 완료. 최신 잔고: {actual_cash:,}원")
            else:
                logger.warning("[SYNC] API로부터 유효한 잔고를 가져오지 못해 동기화에 실패했습니다.")
        except Exception as e:
            logger.error(f"[SYNC] 잔고 동기화 중 오류 발생: {e}")

    def _process_buy(self, candidates: List[Dict]):
        if self.is_buy_stopped:
            logger.info(f"[BUY SKIP] 신규 매수 중단 상태입니다. 사유: {self.stop_buy_reason}")
            return
        if not candidates:
            logger.info("[BUY] 매수 후보 목록이 비어있어 매수 절차를 진행하지 않습니다.")
            return

        MAX_SUBSCRIPTIONS = self.config.get('system', {}).get('max_subscriptions', 40)
        max_pos = self.config.get('trading', {}).get('max_positions', 5)

        # 매수할 후보 종목 찾기 (순회)
        target_candidate = None
        for cand in candidates:
            code = cand['code']
            # 1. 재매수 쿨다운, 2. 이미 보유, 3. 최대 보유 개수 체크
            if code in self.recently_sold:
                logger.debug(f"[BUY SKIP] 후보 건너뜀(쿨다운): {cand['name']}")
                continue
            if code in self.position_manager.positions:
                logger.debug(f"[BUY SKIP] 후보 건너뜀(보유중): {cand['name']}")
                continue
            if code in self.wave_scalpers and self.wave_scalpers[code].position:
                logger.debug(f"[BUY SKIP] 후보 건너뜀(웨이브 스캘퍼 보유중): {cand['name']}")
                continue
            
            # 모든 필터를 통과한 첫 번째 후보를 선택
            target_candidate = cand
            break 

        # 매수할 종목이 없으면 종료
        if not target_candidate:
            if len(self.position_manager.positions) >= max_pos:
                logger.info(f"[BUY SKIP] 최대 보유 종목 개수({max_pos}개)에 도달하여 신규 매수를 건너뜁니다.")
            else:
                logger.info("[BUY SKIP] 모든 후보를 검토했으나 매수할 종목 없음 (쿨다운/보유중)")
            return

        # 최종 선택된 후보로 매수 절차 진행
        code = target_candidate['code']
        name = target_candidate['name']
        normalized_code = self._normalize_code(code) # Use the helper for full normalization

        # 매수 직전에 구독
        if normalized_code not in self.subscribed_codes: # Check normalized code
            if len(self.subscribed_codes) >= MAX_SUBSCRIPTIONS:
                # 슬롯이 꽉 찼을 때, 보유하지 않은 종목 중 하나를 구독 해지하여 공간 확보
                unheld_subscribed = [c for c in self.subscribed_codes if c not in self.position_manager.positions]
                if unheld_subscribed:
                    code_to_unsubscribe = unheld_subscribed[0]
                    self.ws_manager.unsubscribe(code_to_unsubscribe) # This should already be normalized
                    self.subscribed_codes.discard(code_to_unsubscribe)
                    logger.info(f"[SUB] 공간 확보를 위해 구독 해지: {code_to_unsubscribe}")
                else:
                    logger.warning(f"[SUB] 최대 구독 개수 도달. 모든 구독이 보유 종목이므로 {name}을 구독할 수 없습니다.")

            # 다시 한번 슬롯 확인 후 구독
            if len(self.subscribed_codes) < MAX_SUBSCRIPTIONS:
                logger.info(f"[SUB] 매수 대상 신규 구독: {name} ({normalized_code})") # Use normalized_code for logging
                self.ws_manager.subscribe(normalized_code)
                self.subscribed_codes.add(normalized_code) # Add normalized code to subscribed_codes
            else:
                logger.warning(f"[SUB] 공간 확보 실패. {name} ({normalized_code})는 구독 없이 매수됩니다.") # Use normalized_code for logging

        # 가격 정보를 가져오기 위해 최대 3초간 0.5초 간격으로 재시도 (레이스 컨디션 방지)
        current_price = 0
        for _ in range(6): # 0.5초 * 6 = 3초
            price_data = self.market_cache.get_quote_full(normalized_code)
            if price_data and price_data.get('price'):
                current_price = price_data['price']
                break
            time.sleep(0.5)

        if current_price == 0:
            logger.warning(f"[BUY SKIP] 현재가 조회 실패(타임아웃): {name} ({normalized_code})") # Use normalized_code for logging
            # API로 직접 조회하는 fallback 로직 (선택적)
            price_info = self.account_manager.get_stock_price(code)
            if price_info and price_info.get('stck_prpr'):
                current_price = float(price_info.get('stck_prpr'))
                logger.info(f"[BUY] API로 현재가 조회 성공: {name} - {current_price:,}원")
            else:
                return

        # Dynamic position sizing for main strategy
        trading_config = self.config.get('trading', {})
        sizing_method = trading_config.get('position_sizing_method', 'fixed')
        
        buy_amount = 0
        if sizing_method == 'dynamic':
            # 매수 가능 종목 수에 따라 투자 예산을 동적으로 조절 (사용자 제안 로직)
            cash_balance = self.balance_manager.get_balance()
            num_buyable = len(candidates)
            
            # 매수 가능 종목이 있을 경우, 해당 종목 수 만큼 잔고를 분할하여 투자
            if num_buyable > 0:
                buy_amount = cash_balance / num_buyable
                logger.info(f"[BUY_ADAPTIVE_SIZING] 가용 현금 {cash_balance:,.0f}원을 {num_buyable}개 후보로 분할 -> 종목당 {buy_amount:,.0f}원")
            else:
                buy_amount = 0 
        else: # fixed
            buy_amount = trading_config.get('budget_per_stock', 100000)

        min_buy = trading_config.get('min_position_krw', 50000)
        max_buy = trading_config.get('max_position_krw', 1000000)
        buy_amount = np.clip(buy_amount, min_buy, max_buy)

        shares = max(1, int(buy_amount // current_price))

        # 매수 전 잔고 확인 (내부 BalanceManager 사용)
        cash_balance = self.balance_manager.get_balance()
        order_total_amount = shares * current_price
        if cash_balance < order_total_amount:
            logger.warning(f"[BUY SKIP] 내부 잔고 부족으로 매수 건너뜀: {name} (필요: {order_total_amount:,}, 보유: {cash_balance:,})")
            return

        # 주문 정보 로깅
        logger.info(f"[BUY] 매수 주문 시도: {name} {shares}주 @ {current_price:,}원")
        result = self.account_manager.place_buy_order_market(code, shares)
        if result and result.get('success'):
            self._sync_balance() # 잔고 동기화
            self.position_manager.add_position(normalized_code, shares, current_price, name) # Use normalized_code
            trade_summary.record_trade(code=normalized_code, name=name, action='BUY', quantity=shares, price=current_price)
            msg = f"매수 체결: {name} ({normalized_code})\n- 수량: {shares}주\n-- 가격: {current_price:,}원" # Use normalized_code
            logger.info(msg)
            notifier.send_message(msg)
        else:
            error_msg = result.get('error', 'Unknown')
            logger.error(f"[BUY] 매수 주문 실패: {name} ({normalized_code}) {shares}주 @ {current_price:,}원 (총 {order_total_amount:,}원) - 사유: {error_msg}") # Use normalized_code

    def _process_sell_positions(self):
        for code, position in list(self.position_manager.positions.items()):
            if not position or 'price' not in position or 'time' not in position:
                logger.warning(f"[SELL SKIP] 포지션 정보 불완전: {position.get('name', code)}")
                continue

            normalized_code = f"A{code.lstrip('A')}"
            current_price = 0.0
            price_data = self.market_cache.get_quote_full(normalized_code)

            if price_data and price_data.get('price'):
                current_price = float(price_data.get('price'))
            else:
                logger.warning(f"[SELL SKIP] 보유 종목의 현재가 캐시 조회 실패: {position.get('name', code)}. API로 재시도...")
                price_info = self.account_manager.get_stock_price(code)
                if price_info and price_info.get('stck_prpr'):
                    current_price = float(price_info.get('stck_prpr'))
                    logger.info(f"[SELL] API로 현재가 조회 성공: {position.get('name', code)} - {current_price:,}원")
                else:
                    logger.error(f"[SELL FAIL] API로도 현재가 조회 실패: {position.get('name', code)}")
                    continue

            buy_price = float(position['price'])
            if buy_price <= 0:
                logger.warning(f"[SELL SKIP] buy_price=0: {position.get('name', code)}")
                continue

            # --- Peak & Trailing state -------------------------------------------------
            # peak_price는 '진입 이후 최고가'를 지속 기록
            prev_peak = float(position.get('peak_price', 0.0))
            peak_price = max(prev_peak if prev_peak > 0 else buy_price, current_price)
            position['peak_price'] = peak_price  # 상태 저장

            # 트레일링 상태 변수
            trailing_on = position.get('trailing_on', False)

            # --- 수익률 / 보유시간 ------------------------------------------------------
            profit_rate = ((current_price - buy_price) / buy_price) * 100.0
            hold_time = time.time() - float(position['time'])

            # --- ATR-lite (1분봉)로 변동성% 계산 ----------------------------------------
            atr = 0
            atr_pct = 1.2  # 보수적 기본값
            try:
                candles_1m = self.market_cache.get_candles(normalized_code, 1)  # 1분봉
                if candles_1m and len(candles_1m) >= 16:
                    trs = []
                    for i in range(1, 15):
                        h = float(candles_1m[-i]['high'])
                        l = float(candles_1m[-i]['low'])
                        pc = float(candles_1m[-i-1]['close'])
                        tr = max(h - l, abs(h - pc), abs(l - pc))
                        trs.append(tr)
                    atr = sum(trs) / len(trs)
                    last_close = float(candles_1m[-1]['close'])
                    if last_close > 0:
                        atr_pct = (atr / last_close) * 100.0
            except Exception as e:
                logger.debug(f"[SELL] ATR-lite 계산 실패 {position.get('name', code)}: {e}")

            # 트레일 폭(%): max(0.8, 0.6*ATR%) 를 0.8~2.5% 사이로 클램프
            trail_dd_pct = max(0.8, min(0.6 * atr_pct, 2.5))

            # 트레일링 시작/업데이트: 진입 후 +1.0% 이상이면 켬
            if not trailing_on and profit_rate >= 1.0:
                trailing_on = True
                position['trailing_on'] = True
                position['trail_dd_pct'] = trail_dd_pct
            elif trailing_on:
                old = float(position.get('trail_dd_pct', trail_dd_pct))
                position['trail_dd_pct'] = 0.7 * old + 0.3 * trail_dd_pct

            # --- 청산 판단 --------------------------------------------------------------
            should_sell, sell_reason = False, ""

            if profit_rate <= -2.0:
                should_sell = True
                sell_reason = f"손절 ({profit_rate:.1f}%)"

            if not should_sell and atr > 0:
                cut_price = buy_price - (atr * 2)
                if current_price < cut_price:
                    should_sell = True
                    sell_reason = f"ATR손절 ({profit_rate:.1f}%, cut: {cut_price:,.0f})"

            if not should_sell and trailing_on:
                dd_from_peak_pct = ((current_price - peak_price) / peak_price) * 100.0
                trail_dd = float(position.get('trail_dd_pct', trail_dd_pct))
                if dd_from_peak_pct <= -trail_dd:
                    should_sell = True
                    sell_reason = f"추적손절 (+{profit_rate:.1f}%, 고점대비 {dd_from_peak_pct:.1f}%)"

            if not should_sell and profit_rate > 0.5:
                try:
                    if candles_1m and len(candles_1m) >= 4:
                        c_now = float(candles_1m[-1]['close'])
                        c_3ago = float(candles_1m[-4]['close'])
                        if c_3ago > 0:
                            momentum_3m = (c_now - c_3ago) / c_3ago * 100.0
                            if momentum_3m < -0.5:
                                should_sell = True
                                sell_reason = f"모멘텀하락 ({profit_rate:+.1f}%, 3분모멘텀 {momentum_3m:.1f}%)"
                except Exception as e:
                    logger.debug(f"[SELL] 모멘텀 계산 실패 {position.get('name', code)}: {e}")

            if not should_sell and hold_time > 600 and -1.0 < profit_rate < 1.0:
                should_sell = True
                sell_reason = f"횡보정리 ({profit_rate:+.1f}%)"

            if not should_sell and hold_time > 1800:
                should_sell = True
                sell_reason = f"시간만료 ({profit_rate:+.1f}%)"

            # --- 주문 실행 --------------------------------------------------------------
            if should_sell:
                shares_to_sell = int(position['shares'])
                logger.info(f"[SELL] 시장가 매도 주문 시도: {position['name']} ({code}) {shares_to_sell}주 - 사유: {sell_reason}")
                result = self.account_manager.place_sell_order_market(code, shares_to_sell)
                if result and result.get('success'):
                    self.recently_sold[code] = time.time()
                    self._sync_balance() # 잔고 동기화
                    self.position_manager.close_position(
                        code=code,
                        quantity=shares_to_sell,
                        price=current_price,
                        reason=sell_reason,
                        name=position['name']
                    )
                    self.ws_manager.unsubscribe(code)
                    self.subscribed_codes.discard(code)
                    pnl = (current_price - buy_price) * shares_to_sell
                    msg = (
                        f"매도 체결: {position['name']} ({code})\n"
                        f"- 수익률: {profit_rate:+.2f}%\n"
                        f"- 실현손익: {pnl:+,}원"
                    )
                    logger.info(msg)
                    notifier.send_message(msg)
                else:
                    error_msg = (result or {}).get('error', 'Unknown')
                    logger.error(f"[SELL] 매도 주문 실패: {position['name']} ({code}) {shares_to_sell}주 @ {current_price:,}원 - 사유: {error_msg}")



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
        """지정된 날짜의 거래 서머리를 출력합니다."""
        summary_text = trade_summary.get_summary_text(date_str)
        print("\n" + "="*60)
        print(f"거래 서머리 ({date_str or '오늘'})")
        print("="*60)
        print(summary_text)
        print("="*60 + "\n")
        logger.info(f"[SUMMARY] 거래 서머리 출력 완료 ({date_str or '오늘'})")

def load_config() -> Dict:
    try:
        config.print_config_summary()
        return {
            'api': config.get_kis_config(),
            'telegram': config.get_telegram_config(),
            'trading': config.get_trading_config(),
            'system': config.get('system', {})
        }
    except Exception as e:
        logger.error(f"[CONFIG] 설정 로드 실패: {e}")
        return {}
