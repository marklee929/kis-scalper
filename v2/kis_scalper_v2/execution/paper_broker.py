from __future__ import annotations

from typing import Optional

from ..interfaces import PaperBroker
from ..schemas import Action, Fill, Side, TickEvent
from .portfolio import Portfolio


class SimplePaperBroker(PaperBroker):
    def __init__(self, portfolio: Portfolio, fee_rate: float, slippage_rate: float) -> None:
        self.portfolio = portfolio
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def execute(self, action: Action, tick: TickEvent) -> Optional[Fill]:
        if action.side == Side.HOLD or action.size <= 0:
            return None

        if action.side == Side.BUY:
            price = tick.last_price * (1 + self.slippage_rate)
            fee = price * action.size * self.fee_rate
            total = price * action.size + fee
            if self.portfolio.cash < total:
                return None
            return Fill(
                timestamp_ms=tick.timestamp_ms,
                symbol=action.symbol,
                side=action.side,
                size=action.size,
                price=price,
                fee=fee,
                slippage=price * self.slippage_rate,
            )

        if action.side == Side.SELL:
            qty = self.portfolio.position_qty(action.symbol)
            if qty <= 0:
                return None
            sell_size = min(qty, action.size)
            price = tick.last_price * (1 - self.slippage_rate)
            fee = price * sell_size * self.fee_rate
            return Fill(
                timestamp_ms=tick.timestamp_ms,
                symbol=action.symbol,
                side=action.side,
                size=sell_size,
                price=price,
                fee=fee,
                slippage=price * self.slippage_rate,
            )

        return None
