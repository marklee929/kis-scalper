from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..interfaces import BaseLearner, BasePolicy, PaperBroker, TradingEnv
from ..schemas import Action, Observation, Side, TickEvent, Transition
from ..execution.portfolio import Portfolio
from ..market.bar_aggregator import BarAggregator
from ..market.feature_builder import FeatureBuilder
from ..logging.transition_logger import TransitionLogger
from ..logging.summary_logger import SummaryLogger


@dataclass
class ModelBundle:
    model_id: str
    policy: BasePolicy
    learner: BaseLearner
    broker: PaperBroker
    portfolio: Portfolio
    transition_logger: TransitionLogger
    summary_logger: SummaryLogger
    last_equity: float


@dataclass
class RiskGuard:
    max_position_size: float
    cooldown_seconds: int
    max_spread_ratio: float

    def filter_action(self, action: Action, tick: TickEvent, portfolio: Portfolio) -> Action:
        if action.side == Side.HOLD:
            return action
        if self.cooldown_seconds > 0 and tick.timestamp_ms - portfolio.last_trade_ts < self.cooldown_seconds * 1000:
            return Action(timestamp_ms=action.timestamp_ms, symbol=action.symbol, side=Side.HOLD, size=0, confidence=0)
        if action.side == Side.BUY:
            if portfolio.position_qty(action.symbol) + action.size > self.max_position_size:
                return Action(timestamp_ms=action.timestamp_ms, symbol=action.symbol, side=Side.HOLD, size=0, confidence=0)
        if tick.bid_price > 0 and tick.ask_price > 0:
            mid = (tick.bid_price + tick.ask_price) / 2
            spread = tick.ask_price - tick.bid_price
            if mid > 0 and spread / mid > self.max_spread_ratio:
                return Action(timestamp_ms=action.timestamp_ms, symbol=action.symbol, side=Side.HOLD, size=0, confidence=0)
        return action


class RealtimeTradingEnv(TradingEnv):
    def __init__(
        self,
        bar_aggregator: BarAggregator,
        feature_builder: FeatureBuilder,
        risk_guard: RiskGuard,
        models: Iterable[ModelBundle],
    ) -> None:
        self.bar_aggregator = bar_aggregator
        self.feature_builder = feature_builder
        self.risk_guard = risk_guard
        self.models: Dict[str, ModelBundle] = {m.model_id: m for m in models}

    def on_tick(self, tick: TickEvent) -> Iterable[Transition]:
        completed_1s, completed_1m = self.bar_aggregator.update_tick(tick)
        for bar in completed_1s:
            self.feature_builder.update_bar_1s(bar)
        for bar in completed_1m:
            self.feature_builder.update_bar_1m(bar)

        transitions: List[Transition] = []
        if not completed_1s:
            return transitions

        for bundle in self.models.values():
            observation = self.feature_builder.build_observation(tick, bundle.model_id)
            action = bundle.policy.act(observation)
            action = self.risk_guard.filter_action(action, tick, bundle.portfolio)
            fill = bundle.broker.execute(action, tick)
            if fill:
                bundle.portfolio.apply_fill(fill)
            equity = bundle.portfolio.mark_to_market(tick.symbol, tick.last_price)
            reward = equity - bundle.last_equity
            bundle.last_equity = equity
            transition = Transition(
                timestamp_ms=tick.timestamp_ms,
                symbol=tick.symbol,
                model_id=bundle.model_id,
                observation=observation,
                action=action,
                fill=fill,
                reward=reward,
                next_observation=None,
                done=False,
            )
            bundle.learner.update(transition)
            bundle.transition_logger.log(transition)
            bundle.summary_logger.record(transition, equity)
            transitions.append(transition)
        return transitions

    def finalize(self) -> None:
        for bundle in self.models.values():
            bundle.summary_logger.flush()
