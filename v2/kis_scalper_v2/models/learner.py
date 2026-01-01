from __future__ import annotations

from dataclasses import dataclass

from ..interfaces import BaseLearner
from ..schemas import Transition
from .base import RulePolicy


@dataclass
class OnlineBiasLearner(BaseLearner):
    model_id: str
    policy: RulePolicy
    lr: float = 0.0005

    def update(self, transition: Transition) -> None:
        if transition.fill is None:
            return
        if transition.reward > 0:
            self.policy.bias += self.lr
        elif transition.reward < 0:
            self.policy.bias -= self.lr
