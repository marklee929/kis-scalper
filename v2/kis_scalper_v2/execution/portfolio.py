from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from ..schemas import Fill, Side


@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0


@dataclass
class Portfolio:
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    fees_paid: float = 0.0
    slippage_paid: float = 0.0
    last_trade_ts: int = 0

    def apply_fill(self, fill: Fill) -> None:
        pos = self.positions.setdefault(fill.symbol, Position())
        if fill.side == Side.BUY:
            total_cost = fill.price * fill.size + fill.fee
            if pos.qty + fill.size > 0:
                pos.avg_price = (pos.avg_price * pos.qty + fill.price * fill.size) / (pos.qty + fill.size)
            pos.qty += fill.size
            self.cash -= total_cost
        elif fill.side == Side.SELL:
            sell_qty = min(pos.qty, fill.size)
            proceeds = fill.price * sell_qty - fill.fee
            self.cash += proceeds
            self.realized_pnl += (fill.price - pos.avg_price) * sell_qty
            pos.qty -= sell_qty
            if pos.qty <= 0:
                pos.avg_price = 0.0
        self.fees_paid += fill.fee
        self.slippage_paid += fill.slippage
        self.last_trade_ts = fill.timestamp_ms

    def mark_to_market(self, symbol: str, price: float) -> float:
        pos = self.positions.get(symbol)
        if not pos or pos.qty == 0:
            self.unrealized_pnl = 0.0
            return self.cash
        self.unrealized_pnl = (price - pos.avg_price) * pos.qty
        return self.cash + pos.qty * price

    def position_qty(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        return pos.qty if pos else 0.0
