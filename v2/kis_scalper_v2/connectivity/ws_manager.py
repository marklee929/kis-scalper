from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Awaitable, Callable, Iterable, Set

try:
    import websockets
except ImportError:  # pragma: no cover - optional dependency
    websockets = None

from ..config import KISConfig, WebSocketConfig
from ..schemas import TickEvent
from .mock_ws import MockWebSocket
from .tick_normalizer import parse_message, normalize_symbol
from .token_manager import get_approval_key

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(
        self,
        kis: KISConfig,
        ws_config: WebSocketConfig,
        symbols: Iterable[str],
    ) -> None:
        self.kis = kis
        self.ws_config = ws_config
        self._symbols: Set[str] = {normalize_symbol(s) for s in symbols}
        self._stop_event = asyncio.Event()
        self._update_queue: asyncio.Queue[Set[str]] = asyncio.Queue()
        self._desired_symbols: Set[str] = set(self._symbols)

    def update_symbols(self, symbols: Iterable[str]) -> None:
        normalized = {normalize_symbol(s) for s in symbols}
        self._desired_symbols = normalized
        self._update_queue.put_nowait(normalized)

    async def stop(self) -> None:
        self._stop_event.set()

    async def run(self, on_tick: Callable[[TickEvent], Awaitable[None]]) -> None:
        if self.ws_config.mock:
            await self._run_mock(on_tick)
            return
        if websockets is None:
            raise RuntimeError("websockets package is required for real connections")
        await self._run_real(on_tick)

    async def _run_mock(self, on_tick: Callable[[TickEvent], Awaitable[None]]) -> None:
        mock = MockWebSocket(symbols=list(self._symbols), interval=self.ws_config.mock_tick_interval)
        async for tick in mock.stream():
            if self._stop_event.is_set():
                break
            await on_tick(tick)

    async def _run_real(self, on_tick: Callable[[TickEvent], Awaitable[None]]) -> None:
        delay = self.ws_config.reconnect_min_delay
        while not self._stop_event.is_set():
            approval_key = get_approval_key(self.kis)
            try:
                async with websockets.connect(self.ws_config.url, ping_interval=None) as ws:
                    logger.info("websocket connected")
                    await self._subscribe_all(ws, approval_key)
                    heartbeat = asyncio.create_task(self._heartbeat(ws))
                    try:
                        while not self._stop_event.is_set():
                            recv_task = asyncio.create_task(ws.recv())
                            update_task = asyncio.create_task(self._update_queue.get())
                            done, pending = await asyncio.wait(
                                [recv_task, update_task],
                                timeout=1,
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                            for task in pending:
                                task.cancel()
                            for task in done:
                                result = task.result()
                                if isinstance(result, set):
                                    await self._apply_symbol_update(ws, approval_key, result)
                                else:
                                    tick = parse_message(result)
                                    if tick:
                                        await on_tick(tick)
                    finally:
                        heartbeat.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await heartbeat
            except Exception as exc:
                logger.warning("websocket error: %s", exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.ws_config.reconnect_max_delay)
            else:
                delay = self.ws_config.reconnect_min_delay

    async def _heartbeat(self, ws) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(self.ws_config.ping_interval)
            payload = {"header": {"tr_id": "PINGPONG"}}
            try:
                await ws.send(json.dumps(payload))
            except Exception:
                return

    async def _subscribe_all(self, ws, approval_key: str) -> None:
        for symbol in sorted(self._symbols):
            await self._send_subscribe(ws, approval_key, symbol, subscribe=True)

    async def _apply_symbol_update(self, ws, approval_key: str, symbols: Set[str]) -> None:
        current = set(self._symbols)
        new_symbols = set(symbols)
        to_add = new_symbols - current
        to_remove = current - new_symbols
        for symbol in to_remove:
            await self._send_subscribe(ws, approval_key, symbol, subscribe=False)
        for symbol in to_add:
            await self._send_subscribe(ws, approval_key, symbol, subscribe=True)
        self._symbols = new_symbols

    async def _send_subscribe(self, ws, approval_key: str, symbol: str, subscribe: bool) -> None:
        payload = {
            "header": {
                "approval_key": approval_key,
                "custtype": self.kis.custtype,
                "tr_type": "1" if subscribe else "2",
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": self.kis.tr_id,
                    "tr_key": symbol.lstrip("A"),
                }
            },
        }
        await ws.send(json.dumps(payload))
