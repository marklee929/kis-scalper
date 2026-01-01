from __future__ import annotations

from ..schemas import Observation, Side
from .base import RulePolicy


class MomentumPolicy(RulePolicy):
    def act(self, observation: Observation):
        features = observation.merged()
        short_return = features.get("short_return", 0.0)
        volume_z = features.get("volume_z", 0.0)
        breakout = features.get("breakout_flag", 0.0)
        threshold = 0.001 + self.bias
        if short_return > threshold and volume_z > 0 and breakout >= 0.5:
            confidence = min(1.0, abs(short_return) * 100)
            return self._build_action(observation, Side.BUY, confidence)
        if short_return < -threshold:
            confidence = min(1.0, abs(short_return) * 100)
            return self._build_action(observation, Side.SELL, confidence)
        return self._build_action(observation, Side.HOLD, 0.0)
