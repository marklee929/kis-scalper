from __future__ import annotations

from dataclasses import dataclass

from .snapshot import Snapshot


@dataclass(frozen=True)
class ExecutionResult:
    filled: bool
    action: str
    symbol: str
    size: float
    price: float


class ExecutionEngine:
    def execute(self, proposal, decision, snapshot: Snapshot) -> ExecutionResult:
        if not decision.allow or decision.size <= 0:
            return ExecutionResult(
                filled=False,
                action=proposal.action,
                symbol=proposal.symbol,
                size=0.0,
                price=snapshot.last_price,
            )
        return ExecutionResult(
            filled=True,
            action=proposal.action,
            symbol=proposal.symbol,
            size=decision.size,
            price=snapshot.last_price,
        )
