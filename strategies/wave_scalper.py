import time
from collections import deque
from typing import Dict, Optional, List
import numpy as np

from utils.logger import logger

class RollingBuffer:
    """지정된 시간 윈도우 내의 틱 데이터를 관리하는 롤링 버퍼"""
    def __init__(self, window_secs: int):
        self.window_secs = window_secs
        self.ticks = deque()  # (timestamp, price, volume)

    def add(self, tick: Dict):
        """새로운 틱 데이터를 추가하고 오래된 데이터를 제거"""
        ts = tick.get('timestamp', time.time())
        self.ticks.append(tick)
        while self.ticks and ts - self.ticks[0].get('timestamp', 0) > self.window_secs:
            self.ticks.popleft()

    def get_prices(self) -> List[float]:
        return [t['price'] for t in self.ticks]

    def get_volumes(self) -> List[float]:
        return [t.get('exec_vol', t.get('volume', 0)) for t in self.ticks]

    def last_price(self) -> Optional[float]:
        return self.ticks[-1]['price'] if self.ticks else None

class WaveScalper:
    """박스권(횡보) 스캘핑 전략을 실행하는 클래스"""
    def __init__(self, code: str, broker, params: Dict):
        self.code = code
        self.broker = broker
        self.p = params
        self.is_buy_stopped_ref = params.get('is_buy_stopped_ref', lambda: False)
        
        self.state = "IDLE"  # IDLE, RANGING, IN_POSITION, PAUSE
        self.buffer = RollingBuffer(window_secs=self.p['window_secs'])
        self.chan_high: Optional[float] = None
        self.chan_low: Optional[float] = None
        self.last_trade_ts: float = 0
        self.last_recalc_ts: float = 0
        self.position: Optional[Dict] = None  # {'side', 'qty', 'avg_price'}

        # Boot mode attributes
        self.open_ts: Optional[float] = self.p.get('open_time_ref') or None
        self.boot_started_ts: Optional[float] = None
        self.boot_active: bool = False

    def _get_volatility(self) -> float:
        """ATR의 대용으로 가격의 표준편차를 사용"""
        prices = self.buffer.get_prices()
        if len(prices) < 2:
            return 0.0
        return np.std(prices)

    def _dynamic_params(self) -> Dict:
        """채널 폭과 변동성에 기반해 파라미터를 동적으로 조정"""
        if not self.channel_is_valid():
            return {}

        width = self.chan_high - self.chan_low
        mid = (self.chan_high + self.chan_low) / 2
        volatility = self._get_volatility()

        if width == 0 or mid == 0:
            return {}

        width_pct = (width / mid) * 100
        vol_ratio = volatility / width if width > 0 else 0
        enter_band = np.clip(0.1 + 0.5 * vol_ratio, 0.1, 0.25)
        exit_band = np.clip(enter_band - 0.02, 0.1, 0.20)
        tp_pct = max(0.8, 0.6 * width_pct)
        sl_pct = -max(0.6, 0.4 * width_pct)
        
        return {
            'enter_band': enter_band,
            'exit_band': exit_band,
            'take_profit_pct': tp_pct,
            'stop_loss_pct': sl_pct
        }

    def on_tick(self, tick: Dict):
        """매 틱마다 호출되어 전략을 실행"""
        if self.open_ts is None:
            self.open_ts = tick.get('market_open_ts') or tick.get('timestamp', time.time())
            self.boot_started_ts = self.open_ts
            self.boot_active = True
            logger.info(f"[{self.code}] 부트 모드 활성화.")

        self.buffer.add(tick)

        if self.boot_active and time.time() - self.boot_started_ts > self.p.get('boot_duration_secs', 180):
            self.boot_active = False
            logger.info(f"[{self.code}] 부트 모드 비활성화. 일반 모드로 전환.")

        min_pts = self.p.get('boot_min_points', 30) if self.boot_active else self.p.get('min_data_points', 120)
        if len(self.buffer.get_prices()) < min_pts:
            return

        now = time.time()
        if now - self.last_recalc_ts > self.p['recalc_secs']:
            self.recalc_channel()
            self.last_recalc_ts = now

        if self.state in ["IDLE", "PAUSE"]:
            if self.channel_is_valid():
                logger.info(f"[{self.code}] 신규 박스권 감지: {self.chan_low:.2f} - {self.chan_high:.2f} (boot={self.boot_active})")
                self.state = "RANGING"
            return

        if self.state == "RANGING":
            if self.breakout_detected():
                logger.warning(f"[{self.code}] 박스권 이탈 감지! 전략 일시 중지.")
                if self.position:
                    self.try_sell(tick, reason="breakout_stop")
                self.reset_channel(state="PAUSE")
                return

            if self.cooldown_active():
                return

            price = tick['price']
            width = self.chan_high - self.chan_low

            if self.boot_active:
                enter_band = self.p.get('boot_enter_band', 0.10)
                exit_band = self.p.get('boot_exit_band', 0.10)
            else:
                dyn_params = self._dynamic_params()
                enter_band = dyn_params.get('enter_band', self.p['enter_band'])
                exit_band = dyn_params.get('exit_band', self.p['exit_band'])

            if width <= 0: return
            low_band = self.chan_low + enter_band * width
            high_band = self.chan_high - exit_band * width

            # --- Entry Logic ---
            if not self.position and price <= low_band:
                if self.boot_active:
                    # In boot mode, REQUIRE a volume spike to enter (aggressive open strategy)
                    if self.is_vol_spike():
                        self.try_buy(tick)
                else:
                    # In normal mode, AVOID volume spikes (conservative strategy)
                    if not self.is_vol_spike():
                        self.try_buy(tick)

            # --- Exit Logic ---
            if self.position and self.position['side'] == "LONG" and price >= high_band:
                self.try_sell(tick, reason="band_exit")

        if self.position:
            dyn_params = self._dynamic_params()
            self.manage_risk(tick, dyn_params)

    def recalc_channel(self):
        prices = self.buffer.get_prices()
        if not prices:
            return
        
        if self.boot_active:
            self.chan_high = np.percentile(prices, 95)
            self.chan_low = np.percentile(prices, 5)
        else:
            self.chan_high = np.percentile(prices, 98)
            self.chan_low = np.percentile(prices, 2)

    def channel_is_valid(self) -> bool:
        if self.chan_high is None or self.chan_low is None or self.chan_low == 0:
            return False
        
        width = self.chan_high - self.chan_low
        mid = (self.chan_high + self.chan_low) / 2
        if mid == 0: return False
        
        volatility = width / mid
        min_vol = 0.006 if self.boot_active else 0.01
        
        if volatility < min_vol:
            return False
        return True

    def breakout_detected(self) -> bool:
        price = self.buffer.last_price()
        if not price or not self.channel_is_valid(): return False
        
        breakout_margin = (self.chan_high - self.chan_low) * (self.p['breakout_k'] - 1.0)
        return not (self.chan_low - breakout_margin <= price <= self.chan_high + breakout_margin)

    def is_vol_spike(self) -> bool:
        volumes = self.buffer.get_volumes()
        if len(volumes) < 20: return False
        
        recent_vol_avg = np.mean(volumes[-10:])
        base_vol_avg = np.mean(volumes[:-10]) if len(volumes) > 10 else recent_vol_avg
        
        if base_vol_avg == 0: return False
        return recent_vol_avg > self.p['vol_spike_k'] * base_vol_avg

    def try_buy(self, tick: Dict):
        if self.is_buy_stopped_ref():
            logger.info(f"[{self.code}] 매수 금지 상태로 인해 웨이브 스캘핑 매수 건너뜀.")
            return

        price = tick['price']
        buy_amount = tick.get('buy_amount', self.p['position_size_krw'])
        qty = int(buy_amount // price)
        if qty == 0: return

        logger.info(f"[{self.code}] 박스권 하단 시장가 매수 시도: {qty}주 @ {price}")
        result = self.broker.place_buy_order_market(self.code, qty)
        if result and result.get('success'):
            self.state = "IN_POSITION"
            self.position = {"side": "LONG", "qty": qty, "avg_price": price}
            self.last_trade_ts = time.time()
            logger.info(f"[{self.code}] 매수 주문 성공.")
        else:
            error_msg = (result or {}).get('error', 'Unknown error')
            logger.error(f"[{self.code}] 매수 주문 실패: {error_msg}")

    def try_sell(self, tick: Dict, reason: str):
        price = tick['price']
        qty = self.position['qty']
        pnl = (price - self.position['avg_price']) * qty
        logger.info(f"[{self.code}] 시장가 매도 시도 ({reason}): {qty}주 @ {price}, PnL: {pnl:.2f}")
        result = self.broker.place_sell_order_market(self.code, qty)
        if result and result.get('success'):
            self.state = "RANGING"
            self.position = None
            self.last_trade_ts = time.time()
            logger.info(f"[{self.code}] 매도 주문 성공.")
        else:
            error_msg = (result or {}).get('error', 'Unknown error')
            logger.error(f"[{self.code}] 매도 주문 실패: {error_msg}")

    def manage_risk(self, tick: Dict, dyn_params: Optional[Dict] = None):
        if not self.position: return
        
        dyn_params = dyn_params or {}
        stop_loss_pct = dyn_params.get('stop_loss_pct', self.p.get('stop_loss_pct'))
        take_profit_pct = dyn_params.get('take_profit_pct', self.p.get('take_profit_pct'))

        price = tick['price']
        pnl_pct = ((price - self.position["avg_price"]) / self.position["avg_price"]) * 100
        
        if pnl_pct <= stop_loss_pct:
            logger.warning(f"[{self.code}] 손절매 실행. PnL: {pnl_pct:.2f}%")
            self.try_sell(tick, reason="stop_loss")
        elif pnl_pct >= take_profit_pct:
            logger.info(f"[{self.code}] 익절 실행. PnL: {pnl_pct:.2f}%")
            self.try_sell(tick, reason="take_profit")

    def cooldown_active(self) -> bool:
        return time.time() - self.last_trade_ts < self.p['cooldown_secs']

    def reset_channel(self, state="IDLE"):
        self.state = state
        self.chan_high = None
        self.chan_low = None
        logger.info(f"[{self.code}] 채널 리셋. 상태: {self.state}")