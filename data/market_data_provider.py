"""Market data provider abstractions and KIS implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

import logging

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FundamentalSnapshot:
    """Container for simple financial metrics."""

    symbol: str
    debt_to_equity: float
    current_ratio: float
    cash_to_operating_expense_months: float
    revenue_growth: float
    eps_growth: float


@dataclass
class CorporateEvent:
    """Lightweight representation of corporate events."""

    symbol: str
    event_type: str
    timestamp: datetime
    headline: str
    url: Optional[str] = None


class MarketDataProvider(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    def get_daily_history(
        self,
        symbol: str,
        lookback_days: int,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Return end of day OHLCV data."""

    @abstractmethod
    def get_intraday_history(
        self,
        symbol: str,
        period: str = "5d",
        interval: str = "1m",
    ) -> pd.DataFrame:
        """Return intraday OHLCV data."""

    @abstractmethod
    def get_average_volume(self, symbol: str, window: int) -> float:
        """Return rolling average volume."""

    @abstractmethod
    def get_sector_performance(self, lookback_weeks: int) -> pd.DataFrame:
        """Return relative performance for configured sector tickers."""

    @abstractmethod
    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        """Return lightweight fundamental snapshot."""

    @abstractmethod
    def get_recent_events(self, symbol: str) -> List[CorporateEvent]:
        """Return recent corporate events."""

    @abstractmethod
    def stream_quotes(self, symbols: Iterable[str], interval: str = "1m") -> Iterable[pd.DataFrame]:
        """Yield streaming quotes; optional for REST-only providers."""


class KISMarketDataProvider(MarketDataProvider):
    """KIS REST API backed provider used by the integrated trading system."""

    def __init__(
        self,
        account_manager,
        sector_symbols: Optional[List[str]] = None,
    ) -> None:
        from api.account_manager import KISAccountManager  # type: ignore[import-not-found]

        self._manager = account_manager
        self._sector_symbols = sector_symbols or []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_dataframe(rows: List[dict], index_key: str, rename_map: dict) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(rows)
        if index_key in frame.columns:
            frame[index_key] = pd.to_datetime(frame[index_key], errors="coerce")
            frame = frame.dropna(subset=[index_key]).set_index(index_key)
        return frame.rename(columns=rename_map)

    # ------------------------------------------------------------------
    # Interface implementation
    # ------------------------------------------------------------------
    def get_daily_history(
        self,
        symbol: str,
        lookback_days: int,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        candles = self._manager.get_daily_candles(symbol, count=max(lookback_days, 60))
        df = self._to_dataframe(
            candles,
            index_key="date",
            rename_map={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"},
        )
        if not df.empty and end is not None:
            df = df[df.index <= end]
        return df

    def get_intraday_history(
        self,
        symbol: str,
        period: str = "5d",
        interval: str = "1m",
    ) -> pd.DataFrame:
        limit = 240 if interval.endswith("m") else 120
        rows = self._manager.get_intraday_candles(symbol, limit=limit)
        df = self._to_dataframe(
            rows,
            index_key="time",
            rename_map={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"},
        )
        if df.empty:
            logger.debug("[KIS] %s intraday data unavailable, falling back to daily candles", symbol)
            return self.get_daily_history(symbol, lookback_days=20)
        return df

    def get_average_volume(self, symbol: str, window: int) -> float:
        history = self.get_daily_history(symbol, lookback_days=max(window * 2, 40))
        if history.empty:
            return 0.0
        return float(history["Volume"].tail(window).mean())

    def get_sector_performance(self, lookback_weeks: int) -> pd.DataFrame:
        symbols = self._sector_symbols
        if not symbols:
            logger.warning("[KIS] 섹터 코드 목록이 비어 있어 수익률을 계산할 수 없습니다.")
            return pd.DataFrame()

        rows = []
        lookback_days = max(lookback_weeks * 5, 20)
        for code in symbols:
            candles = self._manager.get_daily_candles(code, count=lookback_days + 5)
            if len(candles) < 2:
                logger.debug("[KIS] 섹터 %s 일봉 데이터가 부족합니다: %d건", code, len(candles))
                continue
            try:
                start = float(candles[0].get("close", 0))
                end = float(candles[-1].get("close", 0))
            except (TypeError, ValueError):
                logger.debug("[KIS] 섹터 %s 종가 값을 변환하지 못했습니다: %s → %s", code, candles[0].get("close"), candles[-1].get("close"))
                continue
            if start <= 0:
                logger.debug("[KIS] 섹터 %s 시작 종가가 0 이하입니다: %s", code, start)
                continue
            rows.append({"symbol": code, "return": (end / start) - 1})
        if not rows:
            logger.warning("[KIS] 섹터 수익률 계산 결과가 비어 있습니다. 요청 코드: %s", symbols)
        return pd.DataFrame(rows)

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        try:
            from pykrx import stock  # type: ignore

            today = datetime.now()
            start = (today.replace(year=today.year - 1)).strftime("%Y%m%d")
            end = today.strftime("%Y%m%d")
            df = stock.get_market_fundamental_by_date(start, end, symbol)
            if df.empty:
                raise ValueError("empty fundamentals")
            eps = float(df.iloc[-1].get("EPS", 0) or 0)
            eps_growth = eps / (abs(float(df.iloc[0].get("EPS", 1) or 1)) or 1) - 1 if len(df) > 1 else 0.05
        except Exception:  # noqa: BLE001 - 안전한 기본값 제공
            eps_growth = 0.05

        return FundamentalSnapshot(
            symbol=symbol,
            debt_to_equity=0.5,
            current_ratio=1.5,
            cash_to_operating_expense_months=12.0,
            revenue_growth=0.05,
            eps_growth=eps_growth,
        )

    def get_recent_events(self, symbol: str) -> List[CorporateEvent]:
        # KIS REST API에서 직접 이벤트 목록을 제공하지 않으므로 빈 리스트 반환
        return []

    def stream_quotes(self, symbols: Iterable[str], interval: str = "1m") -> Iterable[pd.DataFrame]:
        raise NotImplementedError("Use web_socket module for realtime streaming")
