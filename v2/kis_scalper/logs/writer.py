from __future__ import annotations

from dataclasses import asdict


class LogWriter:
    def log_action(self, proposal, decision, result, snapshot) -> None:
        raise NotImplementedError


class ConsoleLogWriter(LogWriter):
    def log_action(self, proposal, decision, result, snapshot) -> None:
        payload = {
            "proposal": asdict(proposal),
            "decision": {"allow": decision.allow, "size": decision.size, "reason": decision.reason},
            "result": {
                "filled": result.filled,
                "action": result.action,
                "symbol": result.symbol,
                "size": result.size,
                "price": result.price,
            },
            "snapshot": {"id": snapshot.snapshot_id, "ts": snapshot.timestamp_ms},
        }
        print(payload)
