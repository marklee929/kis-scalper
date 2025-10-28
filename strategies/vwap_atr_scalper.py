import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Deque, Dict, List, Optional, Tuple

import numpy as np

from utils.logger import logger


@dataclass
class MetricsSnapshot:
    timestamp: float
    price: float
    volume: float
    buy_pressure: float
    short_vwap: float
    session_vwap: float
    drift: float
    volume_z: float
    atr: float
    vwap_gradient: float


class RollingVWAP:
    """Rolling VWAP calculator with gradient support."""

    def __init__(self, window_secs: int):
        self.window_secs = window_secs
        self.buffer: Deque[Tuple[float, float, float]] = deque()  # (ts, price, volume)
        self.sum_pv = 0.0
        self.sum_vol = 0.0
        self.history: Deque[Tuple[float, float]] = deque(maxlen=6)

    def update(self, timestamp: float, price: float, volume: float) -> Optional[float]:
        if volume < 0:
            volume = 0.0

        self.buffer.append((timestamp, price, volume))
        self.sum_pv += price * volume
        self.sum_vol += volume

        cutoff = timestamp - self.window_secs
        while self.buffer and self.buffer[0][0] < cutoff:
            ts_old, price_old, volume_old = self.buffer.popleft()
            self.sum_pv -= price_old * volume_old
            self.sum_vol -= volume_old

        value = self.value()
        if value is not None:
            self.history.append((timestamp, value))
        return value

    def value(self) -> Optional[float]:
        if self.sum_vol <= 0:
            return None
        return self.sum_pv / self.sum_vol

    def gradient(self) -> float:
        if len(self.history) < 2:
            return 0.0
        t0, v0 = self.history[0]
        t1, v1 = self.history[-1]
        dt = t1 - t0
        if dt <= 0:
            return 0.0
        return (v1 - v0) / dt


class SessionVWAP:
    """Simple session-wide VWAP tracker."""

    def __init__(self):
        self.sum_pv = 0.0
        self.sum_vol = 0.0

    def update(self, price: float, volume: float) -> Optional[float]:
        if volume <= 0:
            return self.value()
        self.sum_pv += price * volume
        self.sum_vol += volume
        return self.value()

    def value(self) -> Optional[float]:
        if self.sum_vol <= 0:
            return None
        return self.sum_pv / self.sum_vol


class VolumeZScore:
    """Maintains a rolling Z-score for executed volume."""

    def __init__(self, window: int, min_samples: int = 30):
        self.window = window
        self.min_samples = min_samples
        self.volumes: Deque[float] = deque(maxlen=window)

    def update(self, volume: float) -> Optional[float]:
        self.volumes.append(volume)
        if len(self.volumes) < self.min_samples:
            return None
        vols = np.array(self.volumes, dtype=float)
        mean = vols.mean()
        std = vols.std(ddof=1)
        if std < 1e-6:
            return 0.0
        return (vols[-1] - mean) / std


class RollingATR:
    """Rolling ATR calculator using tick-derived ranges."""

    def __init__(self, period: int):
        self.period = period
        self.tr_values: Deque[float] = deque(maxlen=period)
        self.prev_close: Optional[float] = None

    def update(self, price: float, high: Optional[float] = None, low: Optional[float] = None) -> Optional[float]:
        high = high if high is not None else price
        low = low if low is not None else price

        if self.prev_close is None:
            true_range = high - low
        else:
            true_range = max(
                high - low,
                abs(high - self.prev_close),
                abs(low - self.prev_close),
            )

        self.prev_close = price
        self.tr_values.append(true_range)

        if len(self.tr_values) < self.period:
            return None
        return sum(self.tr_values) / len(self.tr_values)


@dataclass
class PositionState:
    side: str
    quantity: int
    avg_price: float
    open_ts: float
    entries: List[Dict] = field(default_factory=list)
    stop: Optional[float] = None
    target1_price: Optional[float] = None
    target1_done: bool = False
    last_metrics: Optional[MetricsSnapshot] = None

    def record_entry(self, qty: int, price: float, ts: float):
        self.entries.append({"qty": qty, "price": price, "ts": ts})


class VWAPATRScalper:
    """
    VWAP drift + liquidity regime scalper template.

    The class expects streaming tick data via `on_tick` and routes order
    requests through the provided `broker` interface.
    """

    DEFAULTS: Dict = {
        "position_size_krw": None,
        "entry_scale": [0.5, 0.3, 0.2],
        "cooldown_secs": 10,
        "focus_window_secs": (15 * 60, 30 * 60),
        "short_vwap_window_secs": 90,
        "volume_z_window": 120,
        "atr_period": 14,
        "drift_threshold": 0.0008,
        "volume_z_min": 0.5,
        "buy_pressure_min": 0.55,
        "trail_pressure_min": 0.50,
        "stop_k": 0.8,
        "trail_k": 0.2,
        "take_profit_k": 1.3,
        "allow_short": False,
        "force_flat_after_focus": True,
        "min_order_qty": 1,
        "log_tag": "VWAP_ATR_SCALPER",
    }

    def __init__(
        self,
        code: str,
        broker,
        settings: Optional[Dict] = None,
        telemetry_writer: Optional[Callable[[Dict], None]] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.code = code
        self.broker = broker
        self.clock = clock
        self.telemetry_writer = telemetry_writer

        self.config = {**self.DEFAULTS, **(settings or {})}
        if not self.config["position_size_krw"]:
            raise ValueError("position_size_krw must be provided in settings.")

        scale = self.config["entry_scale"]
        if not isinstance(scale, (list, tuple)) or not scale:
            raise ValueError("entry_scale must be a non-empty list of fractions.")
        total_scale = sum(scale)
        if total_scale <= 0:
            raise ValueError("entry_scale sum must be positive.")
        self.entry_scale = [weight / total_scale for weight in scale]

        self.short_vwap = RollingVWAP(self.config["short_vwap_window_secs"])
        self.session_vwap = SessionVWAP()
        self.volume_z = VolumeZScore(self.config["volume_z_window"])
        self.atr_tracker = RollingATR(self.config["atr_period"])

        self.position: Optional[PositionState] = None
        self.session_open_ts: Optional[float] = None
        self.cooldown_until: float = 0.0
        self.entry_idx: int = 0
        self.last_exit_ts: float = 0.0
        self.last_tick_ts: Optional[float] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def on_tick(self, tick: Dict):
        """Main entrypoint; call this for every tick update."""
        try:
            self._handle_tick(tick)
        except Exception:
            logger.exception("[%s][%s] tick handling failed.", self.config["log_tag"], self.code)

    # ------------------------------------------------------------------
    # Internal processing
    # ------------------------------------------------------------------
    def _handle_tick(self, tick: Dict):
        price = self._extract_price(tick)
        volume = self._extract_volume(tick)
        if price is None or volume is None:
            return

        ts = self._extract_timestamp(tick)
        self.last_tick_ts = ts
        self._ensure_session_open(ts, tick)

        # Update rolling indicators
        short_vwap = self.short_vwap.update(ts, price, volume)
        session_vwap = self.session_vwap.update(price, volume)
        atr = self.atr_tracker.update(
            price,
            high=tick.get("high") or tick.get("ask_price"),
            low=tick.get("low") or tick.get("bid_price"),
        )
        vol_z = self.volume_z.update(volume)
        buy_pressure = self._extract_buy_pressure(tick, volume)

        if (
            short_vwap is None
            or session_vwap is None
            or atr is None
            or buy_pressure is None
        ):
            return

        drift = (price - short_vwap) / short_vwap if short_vwap else 0.0
        snapshot = MetricsSnapshot(
            timestamp=ts,
            price=price,
            volume=volume,
            buy_pressure=buy_pressure,
            short_vwap=short_vwap,
            session_vwap=session_vwap,
            drift=drift,
            volume_z=vol_z if vol_z is not None else 0.0,
            atr=atr,
            vwap_gradient=self.short_vwap.gradient(),
        )

        if not self._within_focus_window(ts):
            if (
                self.position
                and self.config["force_flat_after_focus"]
                and ts - self.session_open_ts > self.config["focus_window_secs"][1]
            ):
                self._exit_position("focus_window_expired", snapshot, tick)
            return

        if ts < self.cooldown_until:
            return

        if self.position:
            self._manage_position(snapshot, tick)
        else:
            self._attempt_entry(snapshot, tick)

    # ------------------------------------------------------------------
    # Entry / Exit logic
    # ------------------------------------------------------------------
    def _attempt_entry(self, metrics: MetricsSnapshot, tick: Dict):
        if self.entry_idx >= len(self.entry_scale):
            return

        vol_z = metrics.volume_z
        if vol_z is None or vol_z < self.config["volume_z_min"]:
            return

        side = None
        if (
            metrics.drift >= self.config["drift_threshold"]
            and metrics.short_vwap >= metrics.session_vwap
            and metrics.buy_pressure >= self.config["buy_pressure_min"]
        ):
            side = "LONG"
        elif (
            metrics.drift <= -self.config["drift_threshold"]
            and metrics.short_vwap <= metrics.session_vwap
            and (1.0 - metrics.buy_pressure) >= self.config["buy_pressure_min"]
            and self.config["allow_short"]
        ):
            side = "SHORT"

        if side is None:
            return

        qty = self._compute_entry_qty(metrics.price)
        if qty < self.config["min_order_qty"]:
            return

        if not self._execute_entry(side, qty, metrics, tick):
            return

        self.entry_idx += 1
        stop_price = self._initial_stop(side, metrics.price, metrics.atr)
        target_price = self._target_price(side, metrics.price, metrics.atr)
        self.position = PositionState(
            side=side,
            quantity=qty,
            avg_price=metrics.price,
            open_ts=metrics.timestamp,
            stop=stop_price,
            target1_price=target_price,
            last_metrics=metrics,
        )
        self.position.record_entry(qty, metrics.price, metrics.timestamp)
        self._log_trigger("entry", metrics, {"side": side, "qty": qty, "stop": stop_price, "t1": target_price})

    def _manage_position(self, metrics: MetricsSnapshot, tick: Dict):
        assert self.position is not None
        side = self.position.side

        # Scale in when conditions still valid
        if (
            self.entry_idx < len(self.entry_scale)
            and self._entry_conditions_still_valid(metrics, side)
        ):
            qty = self._compute_entry_qty(metrics.price)
            if qty >= self.config["min_order_qty"]:
                if self._execute_entry(side, qty, metrics, tick):
                    prev_qty = self.position.quantity
                    self.position.quantity += qty
                    self.position.avg_price = ((self.position.avg_price * prev_qty) + metrics.price * qty) / self.position.quantity
                    self.position.record_entry(qty, metrics.price, metrics.timestamp)
                    self.position.stop = self._adjust_stop(self.position.stop, side, metrics)
                    self.entry_idx += 1
                    self._log_trigger("scale_in", metrics, {"side": side, "qty": qty})

        # Hard stop
        if self._should_stop(metrics):
            self._exit_position("hard_stop", metrics, tick)
            return

        # Trailing logic
        if self._should_trail_exit(metrics):
            self._exit_position("trail_trigger", metrics, tick)
            return

        # Partial take profit
        if self._should_take_profit(metrics):
            qty = max(self.config["min_order_qty"], self.position.quantity // 2)
            if self._execute_exit(side, qty, metrics, tick):
                self.position.quantity -= qty
                self.position.target1_done = True
                self.position.stop = self._adjust_stop_to_breakeven(side)
                self._log_trigger("take_profit_1", metrics, {"qty": qty, "remaining": self.position.quantity})
                if self.position.quantity <= 0:
                    self._reset_position_state(metrics.timestamp)
                    return

        # Exit when regime reverses
        if self._liquidity_regime_reversed(metrics):
            self._exit_position("regime_reversal", metrics, tick)
            return

        self.position.last_metrics = metrics

    def _exit_position(self, reason: str, metrics: MetricsSnapshot, tick: Dict):
        assert self.position is not None
        qty = self.position.quantity
        if qty <= 0:
            self._reset_position_state(metrics.timestamp)
            return

        if not self._execute_exit(self.position.side, qty, metrics, tick):
            return

        self._log_trigger(reason, metrics, {"qty": qty})
        self._reset_position_state(metrics.timestamp)

    def _reset_position_state(self, timestamp: float):
        self.position = None
        self.entry_idx = 0
        self.last_exit_ts = timestamp
        self.cooldown_until = timestamp + self.config["cooldown_secs"]

    # ------------------------------------------------------------------
    # Condition helpers
    # ------------------------------------------------------------------
    def _entry_conditions_still_valid(self, metrics: MetricsSnapshot, side: str) -> bool:
        if metrics.volume_z is None or metrics.volume_z < self.config["volume_z_min"]:
            return False
        if side == "LONG":
            return (
                metrics.drift >= self.config["drift_threshold"]
                and metrics.short_vwap >= metrics.session_vwap
                and metrics.buy_pressure >= self.config["buy_pressure_min"]
            )
        return (
            metrics.drift <= -self.config["drift_threshold"]
            and metrics.short_vwap <= metrics.session_vwap
            and (1.0 - metrics.buy_pressure) >= self.config["buy_pressure_min"]
        )

    def _should_stop(self, metrics: MetricsSnapshot) -> bool:
        if not self.position or self.position.stop is None:
            return False
        if self.position.side == "LONG":
            return metrics.price <= self.position.stop
        return metrics.price >= self.position.stop

    def _should_trail_exit(self, metrics: MetricsSnapshot) -> bool:
        if not self.position:
            return False
        trail_k = self.config["trail_k"]
        pressure_floor = self.config["trail_pressure_min"]
        if metrics.atr <= 0 or metrics.short_vwap is None:
            return False

        if self.position.side == "LONG":
            price_trigger = metrics.short_vwap - trail_k * metrics.atr
            if metrics.price <= price_trigger:
                return True
            if metrics.buy_pressure < pressure_floor:
                return True
        else:
            price_trigger = metrics.short_vwap + trail_k * metrics.atr
            if metrics.price >= price_trigger:
                return True
            if (1.0 - metrics.buy_pressure) < pressure_floor:
                return True
        return False

    def _should_take_profit(self, metrics: MetricsSnapshot) -> bool:
        if not self.position or self.position.target1_done or self.position.target1_price is None:
            return False
        if self.position.side == "LONG":
            return metrics.price >= self.position.target1_price
        return metrics.price <= self.position.target1_price

    def _liquidity_regime_reversed(self, metrics: MetricsSnapshot) -> bool:
        if not self.position:
            return False
        if self.position.side == "LONG":
            return metrics.drift < 0 or metrics.buy_pressure < 0.5
        return metrics.drift > 0 or (1.0 - metrics.buy_pressure) < 0.5

    # ------------------------------------------------------------------
    # Order helpers
    # ------------------------------------------------------------------
    def _execute_entry(self, side: str, qty: int, metrics: MetricsSnapshot, tick: Dict) -> bool:
        if side == "LONG":
            result = self._place_order("BUY", qty)
        else:
            if not self.config["allow_short"]:
                logger.warning("[%s][%s] Short entry requested but allow_short=False.", self.config["log_tag"], self.code)
                return False
            result = self._place_order("SELL_SHORT", qty)
        success, fill_price = self._parse_order_result(result, metrics.price)
        if not success:
            return False
        slippage = fill_price - metrics.price
        if side == "SHORT":
            slippage = metrics.price - fill_price
        self._emit_telemetry(metrics, slippage, event="entry_fill", extra={"qty": qty, "side": side})
        return True

    def _execute_exit(self, side: str, qty: int, metrics: MetricsSnapshot, tick: Dict) -> bool:
        if side == "LONG":
            result = self._place_order("SELL", qty)
        else:
            result = self._place_order("BUY_TO_COVER", qty)
        success, fill_price = self._parse_order_result(result, metrics.price)
        if not success:
            return False
        slippage = fill_price - metrics.price if side == "SHORT" else metrics.price - fill_price
        self._emit_telemetry(metrics, slippage, event="exit_fill", extra={"qty": qty})
        return True

    def _place_order(self, side: str, qty: int) -> Optional[Dict]:
        """Template adapter for broker orders."""
        if hasattr(self.broker, "place_order"):
            return self.broker.place_order(code=self.code, side=side, qty=qty, order_type="MARKET")
        if side == "BUY" and hasattr(self.broker, "place_buy_order_market"):
            return self.broker.place_buy_order_market(self.code, qty)
        if side == "SELL" and hasattr(self.broker, "place_sell_order_market"):
            return self.broker.place_sell_order_market(self.code, qty)
        if side == "SELL_SHORT" and hasattr(self.broker, "place_short_sell_market"):
            return self.broker.place_short_sell_market(self.code, qty)
        if side == "BUY_TO_COVER" and hasattr(self.broker, "place_buy_to_cover_market"):
            return self.broker.place_buy_to_cover_market(self.code, qty)
        logger.error("[%s][%s] Broker interface missing handler for side=%s", self.config["log_tag"], self.code, side)
        return None

    @staticmethod
    def _parse_order_result(result: Optional[Dict], fallback_price: float) -> Tuple[bool, float]:
        if not result:
            return False, fallback_price
        success = result.get("success") or result.get("ok") or result.get("status") == "FILLED"
        filled_price = result.get("filled_avg_price") or result.get("price") or fallback_price
        return success, float(filled_price)

    def _initial_stop(self, side: str, price: float, atr: float) -> float:
        offset = self.config["stop_k"] * atr
        if side == "LONG":
            return price - offset
        return price + offset

    def _target_price(self, side: str, price: float, atr: float) -> float:
        offset = self.config["take_profit_k"] * atr
        if side == "LONG":
            return price + offset
        return price - offset

    def _adjust_stop(self, current_stop: Optional[float], side: str, metrics: MetricsSnapshot) -> float:
        base_stop = self._initial_stop(side, metrics.price, metrics.atr)
        if current_stop is None:
            return base_stop
        if side == "LONG":
            return max(current_stop, base_stop)
        return min(current_stop, base_stop)

    def _adjust_stop_to_breakeven(self, side: str) -> Optional[float]:
        if not self.position:
            return None
        if side == "LONG":
            return max(self.position.stop or -math.inf, self.position.avg_price)
        return min(self.position.stop or math.inf, self.position.avg_price)

    def _compute_entry_qty(self, price: float) -> int:
        scale_weight = self.entry_scale[self.entry_idx]
        nominal = self.config["position_size_krw"] * scale_weight
        qty = int(nominal // price)
        return max(qty, 0)

    # ------------------------------------------------------------------
    # Data extraction utilities
    # ------------------------------------------------------------------
    def _extract_price(self, tick: Dict) -> Optional[float]:
        price = tick.get("price") or tick.get("close") or tick.get("trade_price")
        return float(price) if price is not None else None

    def _extract_volume(self, tick: Dict) -> Optional[float]:
        volume = tick.get("exec_vol") or tick.get("volume") or tick.get("trade_volume")
        return float(volume) if volume is not None else None

    def _extract_timestamp(self, tick: Dict) -> float:
        ts = tick.get("timestamp") or tick.get("ts")
        if ts is None:
            return self.clock()
        if isinstance(ts, (int, float)):
            return float(ts)
        # Assume string format
        try:
            if len(ts) == 14:  # e.g. YYYYMMDDHHMMSS
                dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
            else:
                dt = datetime.fromisoformat(ts)
            return dt.timestamp()
        except Exception:
            return self.clock()

    def _extract_buy_pressure(self, tick: Dict, volume: float) -> Optional[float]:
        buy_volume = tick.get("buy_volume")
        sell_volume = tick.get("sell_volume")
        if buy_volume is not None and sell_volume is not None:
            total = buy_volume + sell_volume
            if total > 0:
                return float(buy_volume) / float(total)

        buy_strength = tick.get("buy_strength") or tick.get("bid_strength")
        sell_strength = tick.get("sell_strength") or tick.get("ask_strength")
        if buy_strength is not None and sell_strength is not None:
            total = buy_strength + sell_strength
            if total > 0:
                return float(buy_strength) / float(total)

        pressure = tick.get("buy_pressure")
        if pressure is not None:
            return float(pressure)

        # Fall back to neutral value if there is no directional data
        if volume > 0:
            return 0.5
        return None

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------
    def _ensure_session_open(self, ts: float, tick: Dict):
        if self.session_open_ts is not None:
            return
        candidate = tick.get("session_open_ts") or tick.get("market_open_ts")
        if candidate:
            if isinstance(candidate, (int, float)):
                self.session_open_ts = float(candidate)
                return
            try:
                self.session_open_ts = datetime.fromisoformat(candidate).timestamp()
                return
            except ValueError:
                pass

        # Default to 09:00 local session open
        dt = datetime.fromtimestamp(ts)
        session_start = datetime(dt.year, dt.month, dt.day, 9, 0, 0)
        self.session_open_ts = session_start.timestamp()

    def _within_focus_window(self, ts: float) -> bool:
        if self.session_open_ts is None:
            return False
        elapsed = ts - self.session_open_ts
        focus_start, focus_end = self.config["focus_window_secs"]
        return focus_start <= elapsed <= focus_end

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _log_trigger(self, reason: str, metrics: MetricsSnapshot, extra: Optional[Dict] = None):
        payload = {
            "code": self.code,
            "reason": reason,
            "price": round(metrics.price, 4),
            "drift_pct": round(metrics.drift * 100, 4),
            "vol_z": None if metrics.volume_z is None else round(metrics.volume_z, 3),
            "buy_pressure": round(metrics.buy_pressure * 100, 2),
            "atr": round(metrics.atr, 4),
            "short_vwap": round(metrics.short_vwap, 4),
            "session_vwap": round(metrics.session_vwap, 4),
            "gradient": round(metrics.vwap_gradient, 6),
            "timestamp": datetime.fromtimestamp(metrics.timestamp).isoformat(),
        }
        if extra:
            payload.update(extra)
        logger.info("[%s] %s", self.config["log_tag"], payload)
        if self.telemetry_writer:
            self.telemetry_writer(payload)

    def _emit_telemetry(self, metrics: MetricsSnapshot, slippage: float, event: str, extra: Optional[Dict] = None):
        payload = {
            "event": event,
            "code": self.code,
            "price": metrics.price,
            "atr": metrics.atr,
            "drift": metrics.drift,
            "vol_z": metrics.volume_z,
            "buy_pressure": metrics.buy_pressure,
            "slippage": slippage,
            "timestamp": metrics.timestamp,
        }
        if extra:
            payload.update(extra)
        if self.telemetry_writer:
            self.telemetry_writer(payload)
