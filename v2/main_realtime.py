import asyncio
import logging

from kis_scalper_v2.config import load_config
from kis_scalper_v2.connectivity.ws_manager import WebSocketManager
from kis_scalper_v2.env.trading_env import ModelBundle, RealtimeTradingEnv, RiskGuard
from kis_scalper_v2.execution.paper_broker import SimplePaperBroker
from kis_scalper_v2.execution.portfolio import Portfolio
from kis_scalper_v2.logging.summary_logger import SummaryLogger
from kis_scalper_v2.logging.transition_logger import TransitionLogger
from kis_scalper_v2.market.bar_aggregator import BarAggregator
from kis_scalper_v2.market.feature_builder import FeatureBuilder
from kis_scalper_v2.models.learner import OnlineBiasLearner
from kis_scalper_v2.models.momentum import MomentumPolicy
from kis_scalper_v2.models.pullback import PullbackPolicy
from kis_scalper_v2.models.vol_breakout import VolBreakoutPolicy


def build_environment(cfg):
    bar_aggregator = BarAggregator(cfg.data.bar_1s_window, cfg.data.bar_1m_window)
    feature_builder = FeatureBuilder(cfg.data.feature_window_short, cfg.data.feature_window_long)
    risk_guard = RiskGuard(
        max_position_size=cfg.trading.max_position_size,
        cooldown_seconds=cfg.trading.cooldown_seconds,
        max_spread_ratio=cfg.trading.max_spread_ratio,
    )

    models = []
    log_dir = cfg.logging.logs_dir
    transition_prefix = f"{log_dir}/{cfg.logging.transition_prefix}"
    summary_prefix = f"{log_dir}/{cfg.logging.summary_prefix}"

    for model_id, policy_cls in (
        ("momentum", MomentumPolicy),
        ("pullback", PullbackPolicy),
        ("vol_breakout", VolBreakoutPolicy),
    ):
        policy = policy_cls(model_id=model_id, action_size=cfg.model.action_size)
        learner = OnlineBiasLearner(model_id=model_id, policy=policy)
        portfolio = Portfolio(cash=cfg.trading.starting_cash)
        broker = SimplePaperBroker(portfolio, cfg.trading.fee_rate, cfg.trading.slippage_rate)
        transition_logger = TransitionLogger(f"{transition_prefix}_{model_id}.jsonl")
        summary_logger = SummaryLogger(summary_prefix, model_id)
        models.append(
            ModelBundle(
                model_id=model_id,
                policy=policy,
                learner=learner,
                broker=broker,
                portfolio=portfolio,
                transition_logger=transition_logger,
                summary_logger=summary_logger,
                last_equity=cfg.trading.starting_cash,
            )
        )

    return RealtimeTradingEnv(
        bar_aggregator=bar_aggregator,
        feature_builder=feature_builder,
        risk_guard=risk_guard,
        models=models,
    )


async def run_realtime() -> None:
    cfg = load_config()
    env = build_environment(cfg)
    ws_manager = WebSocketManager(cfg.kis, cfg.websocket, cfg.symbols)

    async def on_tick(tick):
        env.on_tick(tick)

    try:
        await ws_manager.run(on_tick)
    finally:
        await ws_manager.stop()
        env.finalize()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_realtime())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
