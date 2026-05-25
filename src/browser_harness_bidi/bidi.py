"""Small WebDriver bidi WebSocket client."""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, Callable

import websockets


class BiDiProtocolError(RuntimeError):
    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}
        self.error = self.payload.get("error")
        self.stacktrace = self.payload.get("stacktrace")


class BiDiClient:
    def __init__(self, url: str, on_event: Callable[[dict[str, Any]], Any] | None = None):
        self.url = url
        self.on_event = on_event
        self.ws = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future] = {}
        self._send_lock = asyncio.Lock()
        self._reader_task: asyncio.Task | None = None

    async def start(self) -> None:
        self.ws = await websockets.connect(self.url, max_size=None)
        self._reader_task = asyncio.create_task(self._read_loop())

    async def close(self) -> None:
        if self.ws is not None:
            await self.ws.close()
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

    async def send(self, method: str, params: dict[str, Any] | None = None, timeout: float | None = 60.0) -> dict[str, Any]:
        if self.ws is None:
            raise RuntimeError("bidi websocket is not connected")
        async with self._send_lock:
            msg_id = self._next_id
            self._next_id += 1
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            self._pending[msg_id] = fut
            message = {"id": msg_id, "method": method, "params": params or {}}
            try:
                await self.ws.send(json.dumps(message))
            except Exception:
                self._pending.pop(msg_id, None)
                raise
        try:
            if timeout is None:
                return await fut
            return await asyncio.wait_for(fut, timeout=timeout)
        except Exception:
            self._pending.pop(msg_id, None)
            raise

    async def _read_loop(self) -> None:
        assert self.ws is not None
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg:
                fut = self._pending.pop(msg["id"], None)
                if fut and not fut.done():
                    if msg.get("type") == "success":
                        fut.set_result(msg.get("result", {}))
                    elif msg.get("type") == "error":
                        err = msg.get("error", "bidi error")
                        text = msg.get("message") or err
                        fut.set_exception(BiDiProtocolError(f"{err}: {text}", msg))
                    else:
                        fut.set_result(msg)
                continue
            if self.on_event is not None:
                outcome = self.on_event(msg)
                if inspect.isawaitable(outcome):
                    await outcome
