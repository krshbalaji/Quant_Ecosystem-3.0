"""
PATCH: quant_ecosystem/orchestration/event_orchestrator.py
FIX:   Constructor now accepts config=None, **kwargs.
"""
from collections import defaultdict


class EventOrchestrator:
    """
    Internal event bus. Engines publish events here; subscribers
    receive them asynchronously (sync stub for PAPER mode).
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type: str, callback):
        """Register a callback for an event type."""
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload=None):
        """Deliver event to all subscribers (synchronous stub)."""
        for cb in self._subscribers.get(event_type, []):
            try:
                cb(payload)
            except Exception as exc:
                print(f"[EventOrchestrator] Error in handler for '{event_type}': {exc}")
