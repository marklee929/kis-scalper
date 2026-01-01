from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..schemas import Transition


@dataclass
class SummaryStats:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_reward: float = 0.0
    fees: float = 0.0
    slippage: float = 0.0
    peak_equity: float = 0.0
    max_drawdown: float = 0.0


class SummaryLogger:
    def __init__(self, path_prefix: str, model_id: str) -> None:
        self.path_prefix = path_prefix
        self.model_id = model_id
        self.stats = SummaryStats()

    def record(self, transition: Transition, equity: float) -> None:
        self.stats.total_reward += transition.reward
        if transition.fill is not None:
            self.stats.trades += 1
            if transition.reward >= 0:
                self.stats.wins += 1
            else:
                self.stats.losses += 1
            self.stats.fees += transition.fill.fee
            self.stats.slippage += transition.fill.slippage
        if equity > self.stats.peak_equity:
            self.stats.peak_equity = equity
        if self.stats.peak_equity > 0:
            drawdown = (self.stats.peak_equity - equity) / self.stats.peak_equity
            if drawdown > self.stats.max_drawdown:
                self.stats.max_drawdown = drawdown

    def flush(self) -> None:
        now = datetime.now().strftime("%Y%m%d")
        path = Path(f"{self.path_prefix}_{self.model_id}_{now}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_id": self.model_id,
            "trades": self.stats.trades,
            "wins": self.stats.wins,
            "losses": self.stats.losses,
            "total_reward": self.stats.total_reward,
            "fees": self.stats.fees,
            "slippage": self.stats.slippage,
            "max_drawdown": self.stats.max_drawdown,
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
