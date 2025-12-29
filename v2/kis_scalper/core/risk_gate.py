from __future__ import annotations

from dataclasses import dataclass

from .snapshot import Snapshot


@dataclass(frozen=True)
class GateDecision:
    allow: bool
    size: float
    reason: str


class RiskGate:
    def __init__(
        self,
        max_daily_loss: float = 100000.0,
        max_exposure_ratio: float = 0.3,
        cooldown_seconds: int = 60,
    ):
        self.max_daily_loss = max_daily_loss
        self.max_exposure_ratio = max_exposure_ratio
        self.cooldown_ms = cooldown_seconds * 1000

    def evaluate(self, proposal, snapshot: Snapshot) -> GateDecision:
        if proposal.action == "HOLD" or proposal.size <= 0:
            return GateDecision(allow=True, size=0.0, reason="hold")

        portfolio = snapshot.portfolio
        loss = max(0.0, portfolio.start_equity - portfolio.equity)
        if proposal.action == "BUY" and loss >= self.max_daily_loss:
            return GateDecision(allow=False, size=0.0, reason="max_daily_loss")

        if proposal.action == "BUY":
            projected_exposure = portfolio.exposure + (proposal.size * snapshot.last_price)
            max_exposure = portfolio.equity * self.max_exposure_ratio
            if projected_exposure > max_exposure:
                return GateDecision(allow=False, size=0.0, reason="max_exposure")

        if proposal.action == "BUY" and portfolio.last_entry_ts:
            if snapshot.timestamp_ms - portfolio.last_entry_ts < self.cooldown_ms:
                return GateDecision(allow=False, size=0.0, reason="cooldown")

        return GateDecision(allow=True, size=proposal.size, reason="ok")
