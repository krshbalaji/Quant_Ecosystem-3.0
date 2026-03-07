"""Shared global event bus with async dispatch, metrics, and history."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Deque, Dict, List, Optional


class GlobalEventBus:
    """Single event bus instance for all engines."""

    def __init__(self, history_limit: int = 1000, queue_limit: int = 5000, **kwargs):
        self._history: Deque[Dict[str, Any]] = deque(maxlen=max(50, int(history_limit)))
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max(100, int(queue_limit)))
        self._subs: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = RLock()
        self._metrics = {
            "published": 0,
            "dropped": 0,
            "dispatched": 0,
            "dispatch_errors": 0,
            "per_type": defaultdict(int),
        }

    def subscribe(self, event_type: str, handler: Callable) -> None:
        key = str(event_type or "*").upper()
        with self._lock:
            if handler not in self._subs[key]:
                self._subs[key].append(handler)

    def handlers_for(self, event_type: str) -> List[Callable]:
        key = str(event_type or "UNKNOWN").upper()
        with self._lock:
            rows = list(self._subs.get(key, []))
            rows.extend(self._subs.get("*", []))
        return rows

    def publish(self, event_or_type: Any, payload: Optional[Dict[str, Any]] = None) -> bool:
        event = self._normalize_event(event_or_type=event_or_type, payload=payload)
        event_type = str(event.get("event_type", "UNKNOWN")).upper()
        with self._lock:
            self._history.append(event)
            self._metrics["published"] += 1
            self._metrics["per_type"][event_type] += 1

        ok = True
        try:
            self._queue.put_nowait(dict(event))
        except asyncio.QueueFull:
            ok = False
            with self._lock:
                self._metrics["dropped"] += 1

        self._dispatch_async(dict(event))
        return ok

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        return self.publish(event_type, payload)

    def put_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> bool:
        return self.publish(event_type, payload)

    async def get_event(self, timeout_sec: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if timeout_sec is None:
            return await self._queue.get()
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=max(0.01, float(timeout_sec)))
        except asyncio.TimeoutError:
            return None

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        n = max(1, int(limit))
        with self._lock:
            rows = list(self._history)
        return rows[-n:]

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            per_type = dict(self._metrics["per_type"])
            out = {
                "published": int(self._metrics["published"]),
                "dropped": int(self._metrics["dropped"]),
                "dispatched": int(self._metrics["dispatched"]),
                "dispatch_errors": int(self._metrics["dispatch_errors"]),
                "per_type": per_type,
                "history_size": len(self._history),
                "queue_size": int(self._queue.qsize()),
            }
        return out

    def _normalize_event(self, event_or_type: Any, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(event_or_type, dict):
            event = dict(event_or_type)
            event.setdefault("event_type", "UNKNOWN")
        else:
            event = dict(payload or {})
            event["event_type"] = str(event_or_type or "UNKNOWN").upper()
        event["event_type"] = str(event.get("event_type", "UNKNOWN")).upper()
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        return event

    def _dispatch_async(self, event: Dict[str, Any]) -> None:
        handlers = self.handlers_for(event.get("event_type"))
        if not handlers:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        for handler in handlers:
            loop.create_task(self._invoke_handler(handler, dict(event)))

    async def _invoke_handler(self, handler: Callable, event: Dict[str, Any]) -> None:
        try:
            out = handler(event)
            if asyncio.iscoroutine(out):
                await out
            with self._lock:
                self._metrics["dispatched"] += 1
        except Exception:
            with self._lock:
                self._metrics["dispatch_errors"] += 1

