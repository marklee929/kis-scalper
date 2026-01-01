from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(slots=True)
class TickEvent:
    timestamp_ms: int
    symbol: str
    last_price: float
    volume: float
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: float = 0.0
    ask_size: float = 0.0
    raw: Optional[dict] = None


@dataclass(slots=True)
class Bar1s:
    symbol: str
    start_ms: int
    end_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    tick_count: int


@dataclass(slots=True)
class Bar1m:
    symbol: str
    start_ms: int
    end_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    bar_count: int


@dataclass(slots=True)
class Observation:
    timestamp_ms: int
    symbol: str
    model_id: str
    base_features: Dict[str, float]
    view_features: Dict[str, float]

    def merged(self) -> Dict[str, float]:
        combined = dict(self.base_features)
        combined.update(self.view_features)
        return combined


@dataclass(slots=True)
class Action:
    timestamp_ms: int
    symbol: str
    side: Side
    size: float
    confidence: float = 0.0


@dataclass(slots=True)
class Fill:
    timestamp_ms: int
    symbol: str
    side: Side
    size: float
    price: float
    fee: float
    slippage: float


@dataclass(slots=True)
class Transition:
    timestamp_ms: int
    symbol: str
    model_id: str
    observation: Observation
    action: Action
    fill: Optional[Fill]
    reward: float
    next_observation: Optional[Observation]
    done: bool
    meta: Dict[str, float] = field(default_factory=dict)
