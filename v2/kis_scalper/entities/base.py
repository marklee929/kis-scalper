from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Proposal:
    entity_id: str
    action: str
    symbol: str
    size: float
    confidence: float
    reason: str


class EntityBase:
    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    def on_snapshot(self, snapshot) -> List[Proposal]:
        raise NotImplementedError
