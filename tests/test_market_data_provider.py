"""Unit tests for KISMarketDataProvider."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path for package-less layout
sys.path.append(str(Path(__file__).resolve().parents[1]))


import pandas as pd



from data.market_data_provider import KISMarketDataProvider


class DummyAccountManager:
    def __init__(self) -> None:
        self.daily_calls = []
        self.intraday_calls = []

    def get_daily_candles(self, stock_code: str, count: int = 120):
        self.daily_calls.append((stock_code, count))
        return [
            {"date": "20250101", "open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": 1000},
            {"date": "20250102", "open": 105.0, "high": 112.0, "low": 102.0, "close": 110.0, "volume": 1500},
        ]

    def get_intraday_candles(self, stock_code: str, limit: int = 120):
        self.intraday_calls.append((stock_code, limit))
        if stock_code == "EMPTY":
            return []
        return [
            {"time": "20250102 090000", "open": 108.0, "high": 111.0, "low": 107.0, "close": 110.0, "volume": 300},
            {"time": "20250102 091000", "open": 110.0, "high": 113.0, "low": 109.0, "close": 112.0, "volume": 500},
        ]


def _make_provider(sector_symbols=None):
    manager = DummyAccountManager()
    provider = KISMarketDataProvider(manager, sector_symbols=sector_symbols or [])
    return manager, provider


def test_daily_history_frame():
    manager, provider = _make_provider()
    df = provider.get_daily_history("005930", lookback_days=2)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert manager.daily_calls, "daily API should be invoked"


def test_intraday_history_uses_api_rows():
    manager, provider = _make_provider()
    df = provider.get_intraday_history("005930")
    assert not df.empty
    assert df.iloc[-1]["Close"] == 112.0
    assert manager.intraday_calls, "intraday API should be invoked"


def test_intraday_fallback_to_daily_when_empty():
    manager, provider = _make_provider()
    df = provider.get_intraday_history("EMPTY")
    assert not df.empty  # fallback should provide data
    assert "Close" in df.columns


def test_sector_performance_aggregates_returns():
    manager, provider = _make_provider(sector_symbols=["SEC001"])
    rows = provider.get_sector_performance(lookback_weeks=1)
    assert not rows.empty
    assert rows.iloc[0]["symbol"] == "SEC001"


def test_fundamentals_returns_defaults():
    _, provider = _make_provider()
    snapshot = provider.get_fundamentals("005930")
    assert snapshot.symbol == "005930"
    assert snapshot.current_ratio >= 0
