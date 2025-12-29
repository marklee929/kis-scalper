from __future__ import annotations

from typing import List, Optional

from .base import EntityBase, Proposal


class MomentumEntity(EntityBase):
    def __init__(self, entity_id: str, symbol: str = "DEMO"):
        super().__init__(entity_id)
        self.symbol = symbol
        self.last_price: Optional[float] = None

    def on_snapshot(self, snapshot) -> List[Proposal]:
        if snapshot.last_price <= 0:
            return [Proposal(self.entity_id, "HOLD", self.symbol, 0.0, 0.0, "no_price")]
        if self.last_price is None:
            self.last_price = snapshot.last_price
            return [Proposal(self.entity_id, "HOLD", self.symbol, 0.0, 0.0, "warmup")]
        action = "BUY" if snapshot.last_price > self.last_price else "HOLD"
        self.last_price = snapshot.last_price
        size = 1.0 if action == "BUY" else 0.0
        return [Proposal(self.entity_id, action, self.symbol, size, 0.5, "demo_momentum")]


class SurvivalEntity(EntityBase):
    def __init__(self, entity_id: str, symbol: str = "DEMO"):
        super().__init__(entity_id)
        self.symbol = symbol
        self.last_price: Optional[float] = None

    def on_snapshot(self, snapshot) -> List[Proposal]:
        position = snapshot.portfolio.positions.get(self.symbol, 0.0)
        if snapshot.last_price <= 0:
            return [Proposal(self.entity_id, "HOLD", self.symbol, 0.0, 0.0, "no_price")]
        if self.last_price is None:
            self.last_price = snapshot.last_price
            return [Proposal(self.entity_id, "HOLD", self.symbol, 0.0, 0.0, "warmup")]
        action = "HOLD"
        size = 0.0
        if position > 0 and snapshot.last_price < self.last_price:
            action = "SELL"
            size = min(1.0, position)
        self.last_price = snapshot.last_price
        return [Proposal(self.entity_id, action, self.symbol, size, 0.6, "demo_survival")]
