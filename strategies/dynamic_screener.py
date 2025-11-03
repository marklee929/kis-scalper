"""데이터 기반 동적 종목 선정 스크리너."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import logging
import numpy as np
import pandas as pd

from data.market_data_provider import (
    FundamentalSnapshot,
    MarketDataProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """스크리너 결과 후보."""

    symbol: str
    name: str
    bias: str
    score: float
    filter_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, object] = field(default_factory=dict)
    news: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """dict 형태로 변환."""

        payload = {
            "code": self.symbol,
            "name": self.name,
            "bias": self.bias,
            "total_score": round(self.score, 2),
            "scores": self.filter_scores,
            "metadata": self.metadata,
        }
        if self.news:
            payload["news"] = self.news
        return payload


@dataclass
class ScreeningResult:
    """스크리닝 결과."""

    closing_candidates: List[Candidate]
    swing_candidates: List[Candidate]
    sector_leaders: List[str]
    market_bias: str


class DynamicScreener:
    """트렌드/모멘텀/기본적 지표를 통합한 스크리너."""

    def __init__(
        self,
        provider: MarketDataProvider,
        settings: Dict[str, object],
        news_fetcher: Optional[object] = None,
    ) -> None:
        self.provider = provider
        self.settings = settings
        self.news_fetcher = news_fetcher

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def screen(self, universe: Optional[Iterable[str]] = None) -> ScreeningResult:
        """주어진 종목군을 분석해 전략별 후보를 반환합니다."""

        universe_symbols = list(universe or self._get_default_universe())
        if not universe_symbols:
            logger.warning("[스크리너] 분석할 종목이 없습니다.")
            return ScreeningResult([], [], [], "neutral")

        sector_result, top_sectors = self._load_sector_performance()
        market_bias = self._determine_market_bias()

        closing: List[Candidate] = []
        swing: List[Candidate] = []

        for symbol in universe_symbols:
            try:
                candidate = self._analyse_symbol(symbol, sector_result, top_sectors, market_bias)
            except Exception as exc:  # pragma: no cover - 방어적 코드
                logger.error("[스크리너] %s 분석 실패: %s", symbol, exc, exc_info=True)
                continue

            if candidate is None:
                continue

            if candidate.bias == "bullish":
                closing.append(candidate)
            else:
                swing.append(candidate)

        closing.sort(key=lambda c: c.score, reverse=True)
        swing.sort(key=lambda c: c.score, reverse=True)

        return ScreeningResult(closing, swing, top_sectors, market_bias)

    # ------------------------------------------------------------------
    # 내부 도우미
    # ------------------------------------------------------------------
    def _get_default_universe(self) -> List[str]:
        universe_cfg = self.settings.get("universe", {})
        return list(universe_cfg.get("default_universe", []))

    def _load_sector_performance(self) -> Tuple[pd.DataFrame, List[str]]:
        cfg = self.settings.get("universe", {})
        weeks = int(cfg.get("sector_preference_window_weeks", 4))
        sector_df = self.provider.get_sector_performance(weeks)
        if sector_df.empty:
            symbols = getattr(self.provider, "_sector_symbols", [])
            logger.warning(
                "[스크리너] 섹터 수익률 데이터를 얻지 못했습니다. 요청 대상: %s",
                symbols or "설정된 섹터 코드 없음",
            )
            return pd.DataFrame(), []

        sector_df = sector_df.sort_values("return", ascending=False).reset_index(drop=True)
        top_n = int(cfg.get("top_sector_count", 3))
        leaders = sector_df.head(top_n)["symbol"].tolist()
        return sector_df, leaders

    def _determine_market_bias(self) -> str:
        cfg = self.settings.get("universe", {})
        benchmark = cfg.get("benchmark_symbol")
        if not benchmark:
            return "neutral"

        history = self.provider.get_daily_history(benchmark, lookback_days=60)
        if history.empty:
            return "neutral"

        recent_return = history["Close"].pct_change().dropna().tail(20).mean()
        if recent_return > 0:
            return "bull"
        if recent_return < 0:
            return "bear"
        return "neutral"

    def _analyse_symbol(
        self,
        symbol: str,
        sector_df: pd.DataFrame,
        leaders: List[str],
        market_bias: str,
    ) -> Optional[Candidate]:
        daily = self.provider.get_daily_history(symbol, lookback_days=int(self.settings.get("multi_timeframe", {}).get("lookback_days", 120)))
        if len(daily) < 60:
            logger.debug("[스크리너] %s 일봉 데이터 부족", symbol)
            return None

        trend_passed, trend_score, trend_bias = self._evaluate_trend(daily)
        if not trend_passed:
            return None

        momentum_passed, momentum_score, momentum_bias = self._evaluate_momentum(daily, trend_bias)
        if not momentum_passed:
            return None

        volume_passed, volume_score = self._evaluate_volume(daily, trend_bias)
        if not volume_passed:
            return None

        fundamental_passed, fundamental_score, snapshot = self._evaluate_fundamentals(symbol)
        if not fundamental_passed:
            return None

        sector_passed, sector_score, sector_name = self._evaluate_sector(symbol, sector_df, leaders)
        if not sector_passed:
            return None

        event_score = self._evaluate_events(symbol)

        multi_timeframe_passed, multi_score = self._evaluate_multi_timeframe(symbol, trend_bias)
        if not multi_timeframe_passed:
            return None

        bias = "bullish" if trend_bias == "up" else "bearish"
        total_score = float(np.mean([trend_score, momentum_score, volume_score, fundamental_score, sector_score, event_score, multi_score]))

        metadata = {
            "trend_bias": trend_bias,
            "momentum_bias": momentum_bias,
            "sector": sector_name,
            "market_bias": market_bias,
            "fundamentals": snapshot.__dict__ if snapshot else {},
        }

        news_items = self._load_latest_news(symbol)

        candidate = Candidate(
            symbol=symbol,
            name=symbol,
            bias=bias,
            score=total_score,
            filter_scores={
                "trend": trend_score,
                "momentum": momentum_score,
                "volume": volume_score,
                "fundamental": fundamental_score,
                "sector": sector_score,
                "event": event_score,
                "multi_timeframe": multi_score,
            },
            metadata=metadata,
            news=news_items,
        )

        return candidate

    # 개별 필터 -----------------------------------------------------------------
    def _evaluate_trend(self, daily: pd.DataFrame) -> Tuple[bool, float, str]:
        cfg = self.settings.get("trend_filter", {})
        short = int(cfg.get("short_window", 20))
        mid = int(cfg.get("mid_window", 50))
        long = int(cfg.get("long_window", 200))
        min_slope = float(cfg.get("min_slope", 0.0))
        min_price_above = float(cfg.get("min_price_above_ma", 0.0))

        close = daily["Close"].astype(float)
        if len(close) < long:
            return False, 0.0, "neutral"

        ma_short = close.rolling(short).mean()
        ma_mid = close.rolling(mid).mean()
        ma_long = close.rolling(long).mean()

        slope_short = ma_short.diff().iloc[-5:].mean()
        slope_mid = ma_mid.diff().iloc[-5:].mean()
        slope_long = ma_long.diff().iloc[-5:].mean()

        price = close.iloc[-1]
        above_short = price / ma_short.iloc[-1] - 1
        above_mid = price / ma_mid.iloc[-1] - 1
        above_long = price / ma_long.iloc[-1] - 1

        is_uptrend = (
            ma_short.iloc[-1] > ma_mid.iloc[-1] > ma_long.iloc[-1]
            and slope_short > min_slope
            and slope_mid > min_slope
            and slope_long > min_slope
            and above_short > min_price_above
        )

        is_downtrend = (
            ma_short.iloc[-1] < ma_mid.iloc[-1] < ma_long.iloc[-1]
            and slope_short < -min_slope
            and slope_mid < -min_slope
            and slope_long < -min_slope
            and above_short < -min_price_above
        )

        if not is_uptrend and not is_downtrend:
            return False, 0.0, "neutral"

        bias = "up" if is_uptrend else "down"
        score = 80 if bias == "up" else 75
        score += float(np.clip(above_short * 100, -10, 10))
        return True, float(np.clip(score, 0, 100)), bias

    def _evaluate_momentum(self, daily: pd.DataFrame, trend_bias: str) -> Tuple[bool, float, str]:
        cfg = self.settings.get("momentum_filter", {})
        rsi_short = int(cfg.get("rsi_short_window", 7))
        rsi_long = int(cfg.get("rsi_long_window", 14))
        rsi_buy_low, rsi_buy_high = cfg.get("rsi_buy_range", [30, 50])
        rsi_sell_low, rsi_sell_high = cfg.get("rsi_sell_range", [50, 70])
        macd_fast = int(cfg.get("macd_fast", 12))
        macd_slow = int(cfg.get("macd_slow", 26))
        macd_signal = int(cfg.get("macd_signal", 9))

        close = daily["Close"].astype(float)
        rsi_fast = self._rsi(close, rsi_short)
        rsi_slow = self._rsi(close, rsi_long)
        if rsi_fast.isna().all() or rsi_slow.isna().all():
            return False, 0.0, "neutral"

        fast_latest = rsi_fast.iloc[-1]
        slow_latest = rsi_slow.iloc[-1]
        crossover = fast_latest - slow_latest

        macd_line, signal_line, hist = self._macd(close, macd_fast, macd_slow, macd_signal)
        macd_latest = macd_line.iloc[-1]
        signal_latest = signal_line.iloc[-1]
        hist_latest = hist.iloc[-1]

        if trend_bias == "up":
            in_range = rsi_buy_low <= fast_latest <= rsi_buy_high
            macd_condition = macd_latest > signal_latest and hist_latest > 0
            bias = "up"
        else:
            in_range = rsi_sell_low <= fast_latest <= rsi_sell_high
            macd_condition = macd_latest < signal_latest and hist_latest < 0
            bias = "down"

        if not in_range or not macd_condition:
            return False, 0.0, "neutral"

        score = 70 + np.clip(crossover, -10, 10)
        score += np.clip(hist_latest * 100, -10, 10)
        return True, float(np.clip(score, 0, 100)), bias

    def _evaluate_volume(self, daily: pd.DataFrame, trend_bias: str) -> Tuple[bool, float]:
        cfg = self.settings.get("volume_filter", {})
        avg_window = int(cfg.get("average_window", 20))
        breakout_multiplier = float(cfg.get("breakout_multiplier", 1.5))
        pullback_multiplier = float(cfg.get("pullback_multiplier", 0.7))

        volume = daily["Volume"].astype(float)
        if len(volume) < avg_window:
            return False, 0.0

        avg_volume = volume.rolling(avg_window).mean().iloc[-1]
        latest_volume = volume.iloc[-1]
        prev_volume = volume.iloc[-2]

        if trend_bias == "up":
            condition = latest_volume >= avg_volume * breakout_multiplier and prev_volume <= avg_volume * pullback_multiplier
        else:
            condition = latest_volume >= avg_volume * breakout_multiplier and prev_volume <= avg_volume

        if not condition:
            return False, 0.0

        score = 60 + np.clip((latest_volume / avg_volume) * 20, 0, 40)
        return True, float(np.clip(score, 0, 100))

    def _evaluate_fundamentals(self, symbol: str) -> Tuple[bool, float, Optional[FundamentalSnapshot]]:
        cfg = self.settings.get("fundamental_filter", {})
        snapshot = self.provider.get_fundamentals(symbol)

        max_de = float(cfg.get("max_debt_to_equity", 1.0))
        min_cr = float(cfg.get("min_current_ratio", 1.0))
        min_cash_months = float(cfg.get("min_cash_to_operating_expense_months", 12))
        min_rev_growth = float(cfg.get("min_revenue_growth", 0.0))
        min_eps_growth = float(cfg.get("min_eps_growth", 0.0))

        checks = [
            snapshot.debt_to_equity <= max_de,
            snapshot.current_ratio >= min_cr,
            snapshot.cash_to_operating_expense_months >= min_cash_months,
            snapshot.revenue_growth >= min_rev_growth,
            snapshot.eps_growth >= min_eps_growth,
        ]

        if not all(checks):
            return False, 0.0, snapshot

        score = 65
        score += (min_cash_months - snapshot.cash_to_operating_expense_months) * -1
        score += (snapshot.revenue_growth + snapshot.eps_growth) * 50
        return True, float(np.clip(score, 0, 100)), snapshot

    def _evaluate_sector(
        self,
        symbol: str,
        sector_df: pd.DataFrame,
        leaders: List[str],
    ) -> Tuple[bool, float, Optional[str]]:
        cfg = self.settings.get("sector_filter", {})
        min_return = float(cfg.get("minimum_relative_return", 0.0))
        exclude_bearish = bool(cfg.get("exclude_bearish", True))
        overrides = cfg.get("sector_overrides", {})

        if sector_df.empty:
            return True, 50.0, None

        sector_symbol = overrides.get(symbol)
        if not sector_symbol:
            return True, 45.0, None

        row = sector_df[sector_df["symbol"] == sector_symbol]
        if row.empty:
            return False, 0.0, sector_symbol

        rel_return = float(row["return"].iloc[0])
        if exclude_bearish and rel_return < min_return:
            return False, 0.0, sector_symbol

        bonus = 10 if sector_symbol in leaders else 0
        score = 55 + rel_return * 100 + bonus
        return True, float(np.clip(score, 0, 100)), sector_symbol

    def _evaluate_events(self, symbol: str) -> float:
        cfg = self.settings.get("event_filter", {})
        include_events = set(cfg.get("include_events", []))
        events = self.provider.get_recent_events(symbol)
        if not events:
            return 50.0

        score = 50.0
        for event in events:
            if event.event_type.lower() in include_events:
                score += 10
        return float(np.clip(score, 0, 100))

    def _evaluate_multi_timeframe(self, symbol: str, trend_bias: str) -> Tuple[bool, float]:
        cfg = self.settings.get("multi_timeframe", {})
        interval = cfg.get("intraday_interval", "4h")
        history = self.provider.get_intraday_history(symbol, period="60d", interval=interval)
        if history.empty:
            return False, 0.0

        close = history["Close"].astype(float)
        ma = close.rolling(20).mean()
        last_close = close.iloc[-1]
        ma_last = ma.iloc[-1]

        if np.isnan(ma_last):
            return False, 0.0

        if trend_bias == "up" and last_close < ma_last:
            return False, 0.0
        if trend_bias == "down" and last_close > ma_last:
            return False, 0.0

        score = 60 + np.clip((last_close / ma_last - 1) * 100, -20, 20)
        return True, float(np.clip(score, 0, 100))

    def _load_latest_news(self, symbol: str) -> List[Dict[str, str]]:
        if not self.news_fetcher:
            return []

        try:
            news_item = self.news_fetcher.search_latest_news(symbol)
        except Exception as exc:  # pragma: no cover - 외부 의존
            logger.debug("[스크리너] %s 뉴스 조회 실패: %s", symbol, exc)
            return []

        if not news_item:
            return []

        title = news_item.get("title")
        if not title:
            return []

        return [
            {
                "title": title,
                "link": news_item.get("link", ""),
                "timestamp": news_item.get("timestamp") or news_item.get("published_at"),
            }
        ]

    # 보조 지표 --------------------------------------------------------------
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

    @staticmethod
    def _macd(series: pd.Series, fast: int, slow: int, signal: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

