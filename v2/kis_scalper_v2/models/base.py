from __future__ import annotations

from dataclasses import dataclass

from ..interfaces import BasePolicy
from ..schemas import Action, Observation, Side


@dataclass
class RulePolicy(BasePolicy):
    model_id: str
    action_size: float
    bias: float = 0.0

    def _build_action(self, observation: Observation, side: Side, confidence: float) -> Action:
        return Action(
            timestamp_ms=observation.timestamp_ms,
            symbol=observation.symbol,
            side=side,
            size=self.action_size,
            confidence=confidence,
        )
