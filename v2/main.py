from kis_scalper.core.event_loop import EventLoop
from kis_scalper.core.events import Event, EventType
from kis_scalper.core.risk_gate import RiskGate
from kis_scalper.core.execution import ExecutionEngine
from kis_scalper.logs.writer import ConsoleLogWriter
from kis_scalper.entities.presets import MomentumEntity, SurvivalEntity


def demo_events():
    price = 100.0
    for i in range(5):
        price += 1.0
        yield Event(
            type=EventType.TICK,
            data={"symbol": "DEMO", "last_price": price, "volume": 1000 + i},
        )


def main():
    risk_gate = RiskGate(max_daily_loss=5000.0, max_exposure_ratio=0.2, cooldown_seconds=30)
    executor = ExecutionEngine()
    logger = ConsoleLogWriter()
    loop = EventLoop(risk_gate=risk_gate, executor=executor, logger=logger)

    loop.register_entity(MomentumEntity(entity_id="momentum_v1", symbol="DEMO"))
    loop.register_entity(SurvivalEntity(entity_id="survival_v1", symbol="DEMO"))

    loop.run(demo_events())


if __name__ == "__main__":
    main()
