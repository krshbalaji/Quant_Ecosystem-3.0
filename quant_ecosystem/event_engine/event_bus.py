"""Async event bus for event-driven trading."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Optional


class EventBus:
    """Central communication hub for publish/subscribe event flow."""

    def __init__(self, max_queue_size: int = 2000, **kwargs):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max(100, int(max_queue_size)))
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        key = str(event_type or "*").upper()
        if handler not in self._subscribers[key]:
            self._subscribers[key].append(handler)

    def publish(self, event: Dict) -> bool:
        if not isinstance(event, dict):
            return False
        evt = dict(event)
        evt.setdefault("event_type", "UNKNOWN")
        evt["event_type"] = str(evt["event_type"]).upper()
        try:
            self._queue.put_nowait(evt)
            return True
        except asyncio.QueueFull:
            return False

    async def get_event(self, timeout_sec: Optional[float] = None) -> Optional[Dict]:
        if timeout_sec is None:
            return await self._queue.get()
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=max(0.01, float(timeout_sec)))
        except asyncio.TimeoutError:
            return None

    def handlers_for(self, event_type: str) -> List[Callable]:
        key = str(event_type or "UNKNOWN").upper()
        handlers = list(self._subscribers.get(key, []))
        handlers.extend(self._subscribers.get("*", []))
        return handlers

