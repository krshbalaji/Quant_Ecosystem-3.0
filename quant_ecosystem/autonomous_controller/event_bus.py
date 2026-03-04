"""Thread-safe internal event bus for Quant Ecosystem orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Event, RLock, Thread
from typing import Any, Callable, Dict, List


EventHandler = Callable[[Dict[str, Any]], None]


@dataclass(frozen=True)
class BusEvent:
    """Canonical event names used inside the autonomous loop."""

    MARKET_UPDATE: str = "MARKET_UPDATE"
    REGIME_CHANGE: str = "REGIME_CHANGE"
    STRATEGY_ACTIVATED: str = "STRATEGY_ACTIVATED"
    STRATEGY_DEACTIVATED: str = "STRATEGY_DEACTIVATED"
    TRADE_EXECUTED: str = "TRADE_EXECUTED"
    RISK_ALERT: str = "RISK_ALERT"


class EventBus:
    """Lightweight thread-safe pub/sub bus with background dispatcher."""

    def __init__(self, queue_size: int = 2000):
        self._subs: Dict[str, List[EventHandler]] = {}
        self._queue: Queue = Queue(maxsize=max(100, int(queue_size)))
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._running = False

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        if not callable(handler):
            return
        key = str(event_name).strip().upper()
        if not key:
            return
        with self._lock:
            self._subs.setdefault(key, []).append(handler)

    def publish(self, event_name: str, payload: Dict[str, Any] | None = None) -> bool:
        key = str(event_name).strip().upper()
        if not key:
            return False
        message = {
            "event": key,
            "payload": payload or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._queue.put_nowait(message)
            return True
        except Exception:
            return False

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop.clear()
            self._thread = Thread(target=self._dispatch_loop, daemon=True, name="event-bus")
            self._thread.start()
            self._running = True

    def stop(self, timeout: float = 2.0) -> None:
        with self._lock:
            if not self._running:
                return
            self._stop.set()
            thread = self._thread
        if thread:
            thread.join(timeout=timeout)
        with self._lock:
            self._thread = None
            self._running = False

    def _dispatch_loop(self) -> None:
        while not self._stop.is_set():
            try:
                message = self._queue.get(timeout=0.25)
            except Empty:
                continue
            except Exception:
                continue

            event_name = str(message.get("event", "")).upper()
            with self._lock:
                handlers = list(self._subs.get(event_name, []))
            for handler in handlers:
                try:
                    handler(message)
                except Exception:
                    # Keep dispatcher fault-tolerant.
                    continue

