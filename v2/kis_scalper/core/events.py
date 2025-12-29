from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class EventType(str, Enum):
    TICK = "TICK"
    BAR = "BAR"
    ORDER_ACK = "ORDER_ACK"
    FILL = "FILL"
    CANCEL_ACK = "CANCEL_ACK"
    BALANCE_UPDATE = "BALANCE_UPDATE"
    POSITION_UPDATE = "POSITION_UPDATE"
    NEWS_SIGNAL = "NEWS_SIGNAL"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"
    LATENCY_ALERT = "LATENCY_ALERT"
    PRICE_SNAPSHOT = "PRICE_SNAPSHOT"
    ORDERBOOK = "ORDERBOOK"


@dataclass(frozen=True)
class Event:
    type: EventType
    data: Dict[str, Any]
