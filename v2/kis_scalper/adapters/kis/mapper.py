from ...core.events import Event, EventType


def map_tick(payload) -> Event:
    return Event(type=EventType.TICK, data=payload)
