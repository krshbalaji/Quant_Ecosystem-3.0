from typing import Any


class MemoryEventAdapter:
    """Adapter that persists events into a MultiMapStore under key = event type name."""

    def __init__(self, store) -> None:
        self._store = store

    def handle_event(self, event: Any) -> None:
        # determine key: if dict with 'event_type' use it; else use class name
        key = None
        try:
            if isinstance(event, dict) and "event_type" in event:
                key = str(event["event_type"])
        except Exception:
            pass
        if key is None:
            key = type(event).__name__
        self._store.put(key, event)


__all__ = ["MemoryEventAdapter"]
