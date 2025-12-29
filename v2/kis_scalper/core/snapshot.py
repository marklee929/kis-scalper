from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .state import MarketState, PortfolioState, SystemHealth


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    timestamp_ms: int
    symbol: str
    last_price: float
    volume: float
    system_health: SystemHealth
    portfolio: PortfolioState
    tags: Dict[str, str]


def build_snapshot(
    snapshot_id: str,
    timestamp_ms: int,
    market: MarketState,
    system: SystemHealth,
    portfolio: PortfolioState,
    tags: Dict[str, str] | None = None,
) -> Snapshot:
    return Snapshot(
        snapshot_id=snapshot_id,
        timestamp_ms=timestamp_ms,
        symbol=market.symbol,
        last_price=market.last_price,
        volume=market.volume,
        system_health=system,
        portfolio=portfolio,
        tags=tags or {},
    )
