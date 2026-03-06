"""Event-driven orchestrator for market events."""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional

from quant_ecosystem.event_engine.event_bus import EventBus
from quant_ecosystem.event_engine.event_handlers import EventHandlers
from quant_ecosystem.event_engine.event_router import EventRouter


class EventDrivenOrchestrator:
    """Consumes bus events and dispatches async handlers."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        event_router: Optional[EventRouter] = None,
        event_handlers: Optional[EventHandlers] = None,
        target_latency_ms: float = 50.0,
    ):
        self.event_bus = event_bus or EventBus()
        self.event_router = event_router or EventRouter()
        self.event_handlers = event_handlers or EventHandlers()
        self.target_latency_ms = max(1.0, float(target_latency_ms))
        self.running = False
        self.last_stats = {
            "processed": 0,
            "last_latency_ms": 0.0,
            "over_target": 0,
            "errors": 0,
        }

    async def run_forever(self, idle_sleep_sec: float = 0.01) -> None:
        self.running = True
        while self.running:
            event = await self.event_bus.get_event(timeout_sec=idle_sleep_sec)
            if not event:
                continue
            started = time.perf_counter()
            try:
                handlers = self.event_router.route(event)
                if not handlers:
                    continue
                for handler_name in handlers:
                    outcome = await self.event_handlers.dispatch(handler_name, event)
                    if not outcome.get("ok", False):
                        self.last_stats["errors"] += 1
            except Exception:
                self.last_stats["errors"] += 1
            finally:
                latency_ms = (time.perf_counter() - started) * 1000.0
                self.last_stats["processed"] += 1
                self.last_stats["last_latency_ms"] = round(latency_ms, 3)
                if latency_ms > self.target_latency_ms:
                    self.last_stats["over_target"] += 1

    def stop(self) -> None:
        self.running = False

    def stats(self) -> Dict:
        return dict(self.last_stats)



# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class EventOrchestrator:
    """Minimal SystemFactory entry-point for event orchestration.

    Delegates to :class:`EventDrivenOrchestrator` when available.
    """

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = EventDrivenOrchestrator()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("EventOrchestrator: delegate unavailable (%s) — stub mode", exc)
        self._log.info("EventOrchestrator initialized")

    def process_event(self, event: dict | None = None) -> dict:
        """Route and handle *event* through the event bus pipeline.

        Returns a result dict with ``status`` and optional metadata.
        Never raises.
        """
        event = event or {}
        if self._delegate is not None:
            try:
                import asyncio as _asyncio
                loop = _asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        self._delegate.dispatch(event)
                    )
                    return result or {"status": "dispatched", "event": event}
                finally:
                    loop.close()
            except Exception as exc:  # noqa: BLE001
                self._log.warning("EventOrchestrator.process_event: delegate error (%s)", exc)
        event_type = event.get("type", "UNKNOWN")
        self._log.debug("EventOrchestrator.process_event: stub handling %s", event_type)
        return {"status": "stub_handled", "event_type": event_type}
