from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..schemas import Transition


class TransitionLogger:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, transition: Transition) -> None:
        payload = _transition_to_dict(transition)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _transition_to_dict(transition: Transition) -> dict:
    payload = asdict(transition)
    payload["action"]["side"] = transition.action.side.value
    if transition.fill:
        payload["fill"]["side"] = transition.fill.side.value
    return payload
