from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..schemas import Bar1m, Bar1s, TickEvent


@dataclass
class _BarBuilder:
    symbol: str
    start_ms: int
    end_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    count: int

    def update(self, price: float, volume: float) -> None:
        self.close = price
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.volume += volume
        self.count += 1


class BarAggregator:
    def __init__(self, bar_1s_window: int, bar_1m_window: int) -> None:
        self._bar_1s_window = bar_1s_window
        self._bar_1m_window = bar_1m_window
        self._current_1s: Dict[str, _BarBuilder] = {}
        self._current_1m: Dict[str, _BarBuilder] = {}
        self.bars_1s: Dict[str, List[Bar1s]] = {}
        self.bars_1m: Dict[str, List[Bar1m]] = {}

    def update_tick(self, tick: TickEvent) -> Tuple[List[Bar1s], List[Bar1m]]:
        completed_1s: List[Bar1s] = []
        completed_1m: List[Bar1m] = []
        sec_bucket = tick.timestamp_ms // 1000
        builder_1s = self._current_1s.get(tick.symbol)
        if builder_1s is None or builder_1s.end_ms // 1000 != sec_bucket:
            if builder_1s is not None:
                completed_1s.append(
                    Bar1s(
                        symbol=builder_1s.symbol,
                        start_ms=builder_1s.start_ms,
                        end_ms=builder_1s.end_ms,
                        open=builder_1s.open,
                        high=builder_1s.high,
                        low=builder_1s.low,
                        close=builder_1s.close,
                        volume=builder_1s.volume,
                        tick_count=builder_1s.count,
                    )
                )
            builder_1s = _BarBuilder(
                symbol=tick.symbol,
                start_ms=sec_bucket * 1000,
                end_ms=(sec_bucket + 1) * 1000 - 1,
                open=tick.last_price,
                high=tick.last_price,
                low=tick.last_price,
                close=tick.last_price,
                volume=tick.volume,
                count=1,
            )
            self._current_1s[tick.symbol] = builder_1s
        else:
            builder_1s.update(tick.last_price, tick.volume)

        for bar in completed_1s:
            bars = self.bars_1s.setdefault(bar.symbol, [])
            bars.append(bar)
            if len(bars) > self._bar_1s_window:
                del bars[0]

            builder_1m = self._current_1m.get(bar.symbol)
            bar_min_bucket = bar.start_ms // 1000 // 60
            if builder_1m is None or builder_1m.end_ms // 1000 // 60 != bar_min_bucket:
                if builder_1m is not None:
                    completed_1m.append(
                        Bar1m(
                            symbol=builder_1m.symbol,
                            start_ms=builder_1m.start_ms,
                            end_ms=builder_1m.end_ms,
                            open=builder_1m.open,
                            high=builder_1m.high,
                            low=builder_1m.low,
                            close=builder_1m.close,
                            volume=builder_1m.volume,
                            bar_count=builder_1m.count,
                        )
                    )
                builder_1m = _BarBuilder(
                    symbol=bar.symbol,
                    start_ms=bar_min_bucket * 60 * 1000,
                    end_ms=(bar_min_bucket + 1) * 60 * 1000 - 1,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    count=1,
                )
                self._current_1m[bar.symbol] = builder_1m
            else:
                builder_1m.update(bar.close, bar.volume)

        for bar in completed_1m:
            bars = self.bars_1m.setdefault(bar.symbol, [])
            bars.append(bar)
            if len(bars) > self._bar_1m_window:
                del bars[0]

        return completed_1s, completed_1m
