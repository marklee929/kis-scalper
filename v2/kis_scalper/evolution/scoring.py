from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    total_pnl: float
    max_drawdown: float
    death_count: int


def score_generation(metrics) -> Score:
    return Score(
        total_pnl=metrics.get("total_pnl", 0.0),
        max_drawdown=metrics.get("max_drawdown", 0.0),
        death_count=metrics.get("death_count", 0),
    )
