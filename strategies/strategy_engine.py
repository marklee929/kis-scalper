"""자동 매매 전략 엔진."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """전략 신호."""

    symbol: str
    action: str  # BUY or SELL
    strategy: str
    price: float
    confidence: float
    timestamp: datetime


@dataclass
class TradePlan:
    """주문 계획."""

    symbol: str
    action: str
    quantity: int
    order_type: str
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    trailing_stop: Optional[float]
    strategy: str
    partial_exit: Optional[List[Dict[str, float]]] = None
    atr: float = 0.0


class MovingAverageCrossoverStrategy:
    """골든/데드 크로스 전략."""

    def __init__(self, short_window: int = 50, long_window: int = 200) -> None:
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        close = data["Close"].astype(float)
        if len(close) < self.long_window + 2:
            return []

        short_ma = close.rolling(self.short_window).mean()
        long_ma = close.rolling(self.long_window).mean()

        prev_short = short_ma.iloc[-2]
        prev_long = long_ma.iloc[-2]
        last_short = short_ma.iloc[-1]
        last_long = long_ma.iloc[-1]

        timestamp = data.index[-1].to_pydatetime() if hasattr(data.index[-1], "to_pydatetime") else datetime.utcnow()
        price = float(close.iloc[-1])
        symbol = getattr(data, "symbol", "")

        signals: List[Signal] = []

        if prev_short < prev_long and last_short > last_long:
            logger.info("[전략] %s 골든크로스 발생: %s", symbol, price)
            signals.append(Signal(symbol, "BUY", "MA_CROSS", price, 0.9, timestamp))
        elif prev_short > prev_long and last_short < last_long:
            logger.info("[전략] %s 데드크로스 발생: %s", symbol, price)
            signals.append(Signal(symbol, "SELL", "MA_CROSS", price, 0.9, timestamp))

        return signals


class RSISwingStrategy:
    """RSI 교차 기반 스윙 전략."""

    def __init__(self, fast_window: int = 7, slow_window: int = 14, lower: float = 30, upper: float = 70) -> None:
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.lower = lower
        self.upper = upper

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        close = data["Close"].astype(float)
        if len(close) < self.slow_window + 2:
            return []

        fast_rsi = self._rsi(close, self.fast_window)
        slow_rsi = self._rsi(close, self.slow_window)

        prev_diff = fast_rsi.iloc[-2] - slow_rsi.iloc[-2]
        last_diff = fast_rsi.iloc[-1] - slow_rsi.iloc[-1]
        timestamp = data.index[-1].to_pydatetime() if hasattr(data.index[-1], "to_pydatetime") else datetime.utcnow()
        price = float(close.iloc[-1])
        symbol = getattr(data, "symbol", "")

        signals: List[Signal] = []

        if fast_rsi.iloc[-1] < self.lower or fast_rsi.iloc[-1] > self.upper:
            return []

        if prev_diff < 0 and last_diff > 0 and fast_rsi.iloc[-1] < self.upper:
            signals.append(Signal(symbol, "BUY", "RSI_SWING", price, 0.7, timestamp))
        elif prev_diff > 0 and last_diff < 0 and fast_rsi.iloc[-1] > self.lower:
            signals.append(Signal(symbol, "SELL", "RSI_SWING", price, 0.7, timestamp))

        return signals

    @staticmethod
    def _rsi(series: pd.Series, window: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi


class BollingerMeanReversionStrategy:
    """볼린저 밴드 기반 평균 회귀 전략."""

    def __init__(self, window: int = 20, num_std: float = 2.0) -> None:
        self.window = window
        self.num_std = num_std

    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        close = data["Close"].astype(float)
        if len(close) < self.window:
            return []

        ma = close.rolling(self.window).mean()
        std = close.rolling(self.window).std()
        upper_band = ma + self.num_std * std
        lower_band = ma - self.num_std * std

        price = float(close.iloc[-1])
        timestamp = data.index[-1].to_pydatetime() if hasattr(data.index[-1], "to_pydatetime") else datetime.utcnow()
        symbol = getattr(data, "symbol", "")

        signals: List[Signal] = []

        if price >= float(upper_band.iloc[-1]):
            signals.append(Signal(symbol, "SELL", "BOLLINGER", price, 0.6, timestamp))
        elif price <= float(lower_band.iloc[-1]):
            signals.append(Signal(symbol, "BUY", "BOLLINGER", price, 0.6, timestamp))

        return signals


class StrategyEngine:
    """복수 전략을 조합하여 거래 계획을 생성하는 엔진."""

    def __init__(self, strategies: Iterable[object]) -> None:
        self.strategies = list(strategies)

    def collect_signals(self, symbol: str, data: pd.DataFrame) -> List[Signal]:
        data = data.copy()
        data.symbol = symbol  # type: ignore[attr-defined]

        signals: List[Signal] = []
        for strategy in self.strategies:
            try:
                strategy_signals = strategy.generate_signals(data)
            except Exception as exc:  # pragma: no cover - 방어 로직
                logger.error("[전략] %s 신호 계산 실패: %s", strategy.__class__.__name__, exc, exc_info=True)
                continue
            signals.extend(strategy_signals)
        return signals

    def build_trade_plan(
        self,
        symbol: str,
        data: pd.DataFrame,
        quantity: int,
        risk_params: Dict[str, float],
    ) -> List[TradePlan]:
        signals = self.collect_signals(symbol, data)
        if not signals:
            return []

        price = float(data["Close"].iloc[-1])
        atr = self._atr(data, period=int(risk_params.get("atr_lookback", 14)))
        atr_value = float(atr.iloc[-1]) if not atr.empty else 0.0
        order_type = "limit" if risk_params.get("allow_limit_orders") else "market"
        partial_exit_plan = risk_params.get("partial_exit_plan")

        plans: List[TradePlan] = []
        for signal in signals:
            stop_loss = None
            take_profit = None
            trailing_stop = None

            if atr_value > 0:
                if signal.action == "BUY":
                    stop_loss = price - atr_value * risk_params.get("stop_loss_atr_multiplier", 1.5)
                    take_profit = price + atr_value * risk_params.get("take_profit_atr_multiplier", 3.0)
                    trailing_stop = price - atr_value * risk_params.get("trailing_stop_atr_multiplier", 1.0)
                else:
                    stop_loss = price + atr_value * risk_params.get("stop_loss_atr_multiplier", 1.5)
                    take_profit = price - atr_value * risk_params.get("take_profit_atr_multiplier", 3.0)
                    trailing_stop = price + atr_value * risk_params.get("trailing_stop_atr_multiplier", 1.0)

            plans.append(
                TradePlan(
                    symbol=symbol,
                    action=signal.action,
                    quantity=quantity,
                    order_type=order_type,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_stop=trailing_stop,
                    strategy=signal.strategy,
                    partial_exit=partial_exit_plan,
                    atr=atr_value,
                )
            )

        return plans

    @staticmethod
    def _atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
        high = data["High"].astype(float)
        low = data["Low"].astype(float)
        close = data["Close"].astype(float)

        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        return atr

