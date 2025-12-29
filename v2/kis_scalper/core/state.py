from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MarketState:
    last_price: float = 0.0
    volume: float = 0.0
    symbol: str = "DEMO"


@dataclass
class PortfolioState:
    cash: float = 0.0
    equity: float = 0.0
    exposure: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    start_equity: float = 0.0
    last_equity: float = 0.0
    last_entry_ts: int = 0
    last_loss_ts: int = 0


@dataclass
class SystemHealth:
    ws_connected: bool = True
    api_latency_ms: float = 0.0
    error_rate: float = 0.0
