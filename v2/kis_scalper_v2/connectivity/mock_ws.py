from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import List

from ..schemas import TickEvent


@dataclass
class MockWebSocket:
    symbols: List[str]
    interval: float = 0.2
    seed: int = 7

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._prices = {symbol: self._rng.uniform(50_000, 150_000) for symbol in self.symbols}

    async def stream(self):
        while True:
            now_ms = int(time.time() * 1000)
            for symbol in self.symbols:
                drift = self._rng.uniform(-1.5, 1.5)
                price = max(1.0, self._prices[symbol] + drift)
                self._prices[symbol] = price
                volume = self._rng.uniform(1, 50)
                spread = max(0.5, price * 0.0002)
                bid = price - spread
                ask = price + spread
                yield TickEvent(
                    timestamp_ms=now_ms,
                    symbol=symbol,
                    last_price=price,
                    volume=volume,
                    bid_price=bid,
                    ask_price=ask,
                    bid_size=self._rng.uniform(1, 20),
                    ask_size=self._rng.uniform(1, 20),
                )
            await asyncio.sleep(self.interval)
