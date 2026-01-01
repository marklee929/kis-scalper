from __future__ import annotations

from ..schemas import Observation, Side
from .base import RulePolicy


class PullbackPolicy(RulePolicy):
    def act(self, observation: Observation):
        features = observation.merged()
        drawdown = features.get("drawdown_from_high", 0.0)
        mean_reversion = features.get("mean_reversion_signal", 0.0)
        recovery = features.get("recovery_slope", 0.0)
        threshold = -0.005 - self.bias
        if drawdown < threshold and recovery > 0:
            confidence = min(1.0, abs(drawdown) * 50)
            return self._build_action(observation, Side.BUY, confidence)
        if mean_reversion < -1.0 and recovery < 0:
            confidence = min(1.0, abs(mean_reversion) / 3)
            return self._build_action(observation, Side.SELL, confidence)
        return self._build_action(observation, Side.HOLD, 0.0)
