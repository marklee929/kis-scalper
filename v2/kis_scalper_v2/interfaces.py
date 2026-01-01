from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional

from .schemas import Action, Fill, Observation, TickEvent, Transition


class BasePolicy(ABC):
    model_id: str

    @abstractmethod
    def act(self, observation: Observation) -> Action:
        raise NotImplementedError


class BaseLearner(ABC):
    model_id: str

    @abstractmethod
    def update(self, transition: Transition) -> None:
        raise NotImplementedError


class PaperBroker(ABC):
    @abstractmethod
    def execute(self, action: Action, tick: TickEvent) -> Optional[Fill]:
        raise NotImplementedError


class TradingEnv(ABC):
    @abstractmethod
    def on_tick(self, tick: TickEvent) -> Iterable[Transition]:
        raise NotImplementedError

    @abstractmethod
    def finalize(self) -> None:
        raise NotImplementedError
