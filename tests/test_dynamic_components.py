"""Dynamic screener & strategy engine tests."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from data.market_data_provider import (
    CorporateEvent,
    FundamentalSnapshot,
    MarketDataProvider,
)
from strategies.dynamic_screener import DynamicScreener
from strategies.strategy_engine import StrategyEngine, Signal, TradePlan


class DummyProvider(MarketDataProvider):
    """Fake provider for unit tests."""

    def __init__(self) -> None:
        base_date = datetime(2024, 1, 1)
        dates = pd.date_range(base_date, periods=120, freq="D")
        close = pd.Series([100 + i + 0.1 * i ** 2 for i in range(120)], index=dates, dtype=float)
        volume = pd.Series([100000 + i for i in range(120)], index=dates, dtype=float)
        self.daily = pd.DataFrame({
            "Open": close - 1,
            "High": close + 1,
            "Low": close - 2,
            "Close": close,
            "Volume": volume,
        })
        intraday_index = pd.date_range(base_date, periods=40, freq="4h")
        intraday_close = pd.Series([200 + i + 0.05 * i ** 2 for i in range(40)], index=intraday_index, dtype=float)
        self.intraday = pd.DataFrame({
            "Open": intraday_close - 1,
            "High": intraday_close + 1,
            "Low": intraday_close - 2,
            "Close": intraday_close,
        })
        self.fundamental = FundamentalSnapshot(
            symbol="TEST",
            debt_to_equity=0.3,
            current_ratio=2.0,
            cash_to_operating_expense_months=18,
            revenue_growth=0.1,
            eps_growth=0.1,
        )

    def get_daily_history(self, symbol: str, lookback_days: int, end=None) -> pd.DataFrame:
        return self.daily.copy()

    def get_intraday_history(self, symbol: str, period: str = "5d", interval: str = "1m") -> pd.DataFrame:
        return self.intraday.copy()

    def get_average_volume(self, symbol: str, window: int) -> float:
        return float(self.daily["Volume"].tail(window).mean())

    def get_sector_performance(self, lookback_weeks: int) -> pd.DataFrame:
        return pd.DataFrame([
            {"symbol": "XLY", "return": 0.05},
            {"symbol": "XLV", "return": 0.02},
        ])

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        return self.fundamental

    def get_recent_events(self, symbol: str):
        return [
            CorporateEvent(symbol=symbol, event_type="earnings", timestamp=datetime.utcnow(), headline="earnings"),
        ]

    def stream_quotes(self, symbols, interval: str = "1m"):
        raise NotImplementedError


class FriendlyScreener(DynamicScreener):
    """Screener with relaxed momentum filter for deterministic tests."""

    def _evaluate_momentum(self, daily: pd.DataFrame, trend_bias: str):  # type: ignore[override]
        return True, 80.0, trend_bias


def test_dynamic_screener_returns_candidate():
    provider = DummyProvider()
    settings = {
        "universe": {"default_universe": ["TEST"], "benchmark_symbol": "^KS11", "sector_preference_window_weeks": 4, "top_sector_count": 3},
        "trend_filter": {"short_window": 5, "mid_window": 10, "long_window": 20, "min_slope": -1, "min_price_above_ma": -1},
        "momentum_filter": {
            "rsi_short_window": 7,
            "rsi_long_window": 14,
            "rsi_buy_range": [0, 100],
            "rsi_sell_range": [0, 100],
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
        },
        "volume_filter": {"average_window": 5, "breakout_multiplier": 0.5, "pullback_multiplier": 10.0},
        "sector_filter": {"minimum_relative_return": -1, "exclude_bearish": False, "sector_overrides": {"TEST": "XLY"}},
        "fundamental_filter": {
            "max_debt_to_equity": 1.0,
            "min_current_ratio": 1.0,
            "min_cash_to_operating_expense_months": 6,
            "min_revenue_growth": 0.0,
            "min_eps_growth": 0.0,
        },
        "event_filter": {"include_events": ["earnings"]},
        "multi_timeframe": {"intraday_interval": "4h", "lookback_days": 60},
    }

    screener = FriendlyScreener(provider, settings)
    result = screener.screen(["TEST"])

    assert result.closing_candidates, "Expected bullish candidate"
    candidate = result.closing_candidates[0]
    assert candidate.symbol == "TEST"


class DummyStrategy:
    def generate_signals(self, data: pd.DataFrame):
        return [
            Signal(
                symbol=getattr(data, "symbol", "TEST"),
                action="BUY",
                strategy="DUMMY",
                price=float(data["Close"].iloc[-1]),
                confidence=1.0,
                timestamp=datetime.utcnow(),
            )
        ]


def test_strategy_engine_builds_trade_plan():
    data_index = pd.date_range(datetime(2024, 1, 1), periods=30, freq="D")
    close = pd.Series([100 + i for i in range(30)], index=data_index, dtype=float)
    frame = pd.DataFrame({
        "Open": close - 1,
        "High": close + 1,
        "Low": close - 2,
        "Close": close,
    })

    engine = StrategyEngine([DummyStrategy()])
    risk_params = {
        "atr_lookback": 5,
        "allow_limit_orders": True,
        "stop_loss_atr_multiplier": 1.5,
        "take_profit_atr_multiplier": 2.0,
        "trailing_stop_atr_multiplier": 1.0,
        "partial_exit_plan": [{"pct": 0.5, "target_multiple": 1.5}],
    }

    plans = engine.build_trade_plan("TEST", frame, quantity=10, risk_params=risk_params)

    assert plans, "Trade plan should be generated"
    plan = plans[0]
    assert isinstance(plan, TradePlan)
    assert plan.quantity == 10
    assert plan.order_type == "limit"
    assert plan.stop_loss is not None
