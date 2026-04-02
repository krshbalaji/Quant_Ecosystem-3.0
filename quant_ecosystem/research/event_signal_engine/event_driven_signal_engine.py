"""
PATCH: quant_ecosystem/events/event_driven_signal_engine.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class EventDrivenSignalEngine:
    """
    Generates trading signals from discrete market events
    (earnings, macro releases, news sentiment, etc.).
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._handlers = {}

    def register_event(self, event_type: str, handler):
        """Register a handler callable for a given event type."""
        self._handlers[event_type] = handler

    def process(self, event: dict):
        """Route an event dict to its registered handler (stub)."""
        handler = self._handlers.get(event.get("type"))
        if handler:
            return handler(event)
        return None
