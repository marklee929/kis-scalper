from __future__ import annotations

import math
from collections import deque
from typing import Deque, Dict, List

from ..schemas import Bar1m, Bar1s, Observation, TickEvent


class FeatureBuilder:
    def __init__(self, short_window: int, long_window: int) -> None:
        self.short_window = short_window
        self.long_window = long_window
        self._bars_1s: Dict[str, Deque[Bar1s]] = {}
        self._bars_1m: Dict[str, Deque[Bar1m]] = {}

    def update_bar_1s(self, bar: Bar1s) -> None:
        dq = self._bars_1s.setdefault(bar.symbol, deque(maxlen=self.long_window))
        dq.append(bar)

    def update_bar_1m(self, bar: Bar1m) -> None:
        dq = self._bars_1m.setdefault(bar.symbol, deque(maxlen=self.long_window))
        dq.append(bar)

    def build_observation(self, tick: TickEvent, model_id: str) -> Observation:
        bars_1s = list(self._bars_1s.get(tick.symbol, deque()))
        base = self._base_features(tick, bars_1s)
        view = self._view_features(model_id, tick, bars_1s)
        return Observation(
            timestamp_ms=tick.timestamp_ms,
            symbol=tick.symbol,
            model_id=model_id,
            base_features=base,
            view_features=view,
        )

    def _base_features(self, tick: TickEvent, bars_1s: List[Bar1s]) -> Dict[str, float]:
        closes = [b.close for b in bars_1s]
        volumes = [b.volume for b in bars_1s]
        base = {
            "last_price": tick.last_price,
            "spread": max(0.0, tick.ask_price - tick.bid_price),
            "return_1s": _return(closes, 1),
            "return_5s": _return(closes, 5),
            "return_30s": _return(closes, min(self.short_window, 30)),
            "volume_1s": volumes[-1] if volumes else 0.0,
            "volume_z": _zscore(volumes),
        }
        base["realized_vol"] = _realized_vol(closes, window=min(self.short_window, 30))
        return base

    def _view_features(self, model_id: str, tick: TickEvent, bars_1s: List[Bar1s]) -> Dict[str, float]:
        closes = [b.close for b in bars_1s]
        highs = [b.high for b in bars_1s]
        lows = [b.low for b in bars_1s]
        volumes = [b.volume for b in bars_1s]
        short_return = _return(closes, self.short_window)
        orderbook_imbalance = _imbalance(tick.bid_size, tick.ask_size)
        breakout_flag = 1.0 if closes and closes[-1] >= max(highs[-self.short_window :], default=closes[-1]) else 0.0
        drawdown_from_high = _drawdown_from_high(closes, highs)
        mean_reversion_signal = -_zscore(closes)
        recovery_slope = _slope(closes, window=5)
        realized_vol = _realized_vol(closes, window=self.short_window)
        long_vol = _realized_vol(closes, window=self.long_window)
        vol_regime = realized_vol / long_vol if long_vol > 0 else 1.0
        range_breakout_signal = _range_breakout(closes, highs, lows, window=self.long_window)

        if model_id == "momentum":
            return {
                "short_return": short_return,
                "volume_z": _zscore(volumes),
                "orderbook_imbalance": orderbook_imbalance,
                "breakout_flag": breakout_flag,
            }
        if model_id == "pullback":
            return {
                "drawdown_from_high": drawdown_from_high,
                "mean_reversion_signal": mean_reversion_signal,
                "recovery_slope": recovery_slope,
            }
        if model_id == "vol_breakout":
            return {
                "realized_vol": realized_vol,
                "vol_regime": vol_regime,
                "range_breakout_signal": range_breakout_signal,
            }
        return {}


def _return(closes: List[float], window: int) -> float:
    if len(closes) <= window:
        return 0.0
    start = closes[-window - 1]
    if start == 0:
        return 0.0
    return closes[-1] / start - 1.0


def _zscore(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (values[-1] - mean) / std


def _realized_vol(closes: List[float], window: int) -> float:
    if len(closes) <= 1:
        return 0.0
    window = max(2, min(window, len(closes) - 1))
    returns = []
    for i in range(-window, -1):
        prev = closes[i]
        cur = closes[i + 1]
        if prev == 0:
            continue
        returns.append(cur / prev - 1.0)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance)


def _imbalance(bid_size: float, ask_size: float) -> float:
    denom = bid_size + ask_size
    if denom <= 0:
        return 0.0
    return (bid_size - ask_size) / denom


def _drawdown_from_high(closes: List[float], highs: List[float]) -> float:
    if not closes or not highs:
        return 0.0
    peak = max(highs)
    if peak <= 0:
        return 0.0
    return (closes[-1] - peak) / peak


def _slope(closes: List[float], window: int) -> float:
    if len(closes) <= window:
        return 0.0
    return (closes[-1] - closes[-window - 1]) / float(window)


def _range_breakout(closes: List[float], highs: List[float], lows: List[float], window: int) -> float:
    if not closes:
        return 0.0
    highs_window = highs[-window:] if highs else []
    lows_window = lows[-window:] if lows else []
    if not highs_window or not lows_window:
        return 0.0
    last = closes[-1]
    if last > max(highs_window):
        return 1.0
    if last < min(lows_window):
        return -1.0
    return 0.0
