from __future__ import annotations

from ..schemas import Observation, Side
from .base import RulePolicy


class VolBreakoutPolicy(RulePolicy):
    def act(self, observation: Observation):
        features = observation.merged()
        breakout = features.get("range_breakout_signal", 0.0)
        vol_regime = features.get("vol_regime", 1.0)
        threshold = 1.0 + self.bias
        if breakout > 0 and vol_regime >= threshold:
            confidence = min(1.0, vol_regime - 1.0)
            return self._build_action(observation, Side.BUY, confidence)
        if breakout < 0 and vol_regime >= threshold:
            confidence = min(1.0, vol_regime - 1.0)
            return self._build_action(observation, Side.SELL, confidence)
        return self._build_action(observation, Side.HOLD, 0.0)
