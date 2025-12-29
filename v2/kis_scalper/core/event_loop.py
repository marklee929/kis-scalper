from __future__ import annotations

import time
import uuid
from typing import Iterable, List

from .events import Event, EventType
from .execution import ExecutionEngine
from .risk_gate import RiskGate
from .snapshot import build_snapshot
from .state import MarketState, PortfolioState, SystemHealth
from ..logs.writer import LogWriter


class EventLoop:
    def __init__(
        self,
        risk_gate: RiskGate,
        executor: ExecutionEngine,
        logger: LogWriter,
        starting_cash: float = 1_000_000.0,
    ):
        self.risk_gate = risk_gate
        self.executor = executor
        self.logger = logger
        self.entities = []
        self.market = MarketState()
        self.portfolio = PortfolioState(cash=starting_cash, equity=starting_cash, start_equity=starting_cash)
        self.portfolio.last_equity = starting_cash
        self.system = SystemHealth()

    def register_entity(self, entity) -> None:
        self.entities.append(entity)

    def run(self, events: Iterable[Event]) -> None:
        for event in events:
            self.process_event(event)

    def process_event(self, event: Event) -> None:
        self._update_state(event)
        self._mark_to_market()
        snapshot = build_snapshot(
            snapshot_id=str(uuid.uuid4()),
            timestamp_ms=int(time.time() * 1000),
            market=self.market,
            system=self.system,
            portfolio=self.portfolio,
        )
        proposals = self._collect_proposals(snapshot)
        for proposal in proposals:
            decision = self.risk_gate.evaluate(proposal, snapshot)
            result = self.executor.execute(proposal, decision, snapshot)
            if result.filled:
                self._apply_fill(result, snapshot.timestamp_ms)
                self._mark_to_market()
            self.logger.log_action(proposal, decision, result, snapshot)

    def _update_state(self, event: Event) -> None:
        if event.type == EventType.TICK:
            self.market.last_price = float(event.data.get("last_price", self.market.last_price))
            self.market.volume = float(event.data.get("volume", self.market.volume))
            self.market.symbol = str(event.data.get("symbol", self.market.symbol))

    def _collect_proposals(self, snapshot) -> List:
        proposals = []
        for entity in self.entities:
            proposals.extend(entity.on_snapshot(snapshot))
        return proposals

    def _mark_to_market(self) -> None:
        position_qty = self.portfolio.positions.get(self.market.symbol, 0.0)
        position_value = position_qty * self.market.last_price
        self.portfolio.exposure = abs(position_value)
        self.portfolio.equity = self.portfolio.cash + position_value
        if self.portfolio.equity < self.portfolio.last_equity:
            self.portfolio.last_loss_ts = int(time.time() * 1000)
        self.portfolio.last_equity = self.portfolio.equity

    def _apply_fill(self, result, timestamp_ms: int) -> None:
        if result.action == "BUY":
            cost = result.size * result.price
            self.portfolio.cash -= cost
            self.portfolio.positions[result.symbol] = self.portfolio.positions.get(result.symbol, 0.0) + result.size
            self.portfolio.last_entry_ts = timestamp_ms
        elif result.action == "SELL":
            qty = self.portfolio.positions.get(result.symbol, 0.0)
            sell_size = min(qty, result.size)
            self.portfolio.cash += sell_size * result.price
            self.portfolio.positions[result.symbol] = max(0.0, qty - sell_size)
