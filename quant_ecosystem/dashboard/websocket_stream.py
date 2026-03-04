"""WebSocket streaming hub for dashboard clients."""

from __future__ import annotations

import asyncio
import json
from typing import Set


class WebSocketStreamHub:
    """Fan-out hub for dashboard event/state messages."""

    def __init__(self):
        self._clients: Set[object] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, message: dict) -> int:
        payload = json.dumps(message, separators=(",", ":"), default=str)
        async with self._lock:
            clients = list(self._clients)
        sent = 0
        for ws in clients:
            try:
                await ws.send_text(payload)
                sent += 1
            except Exception:
                await self.disconnect(ws)
        return sent

    async def heartbeat_loop(self, state_api, interval_sec: float = 0.5):
        interval = max(0.1, float(interval_sec))
        try:
            while True:
                state = state_api.get_system_state()
                await self.broadcast({"type": "system_state", "data": state})
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
        # graceful shutdown
            return
