"""
QE3 Event Registry
Pack24
"""


class EventRegistry:
    """
    Duplicate event protection / replay protection
    """

    def __init__(self):
        self._seen_event_ids = set()

    def seen(self, event_id: str):
        return event_id in self._seen_event_ids

    def mark_seen(self, event_id: str):
        self._seen_event_ids.add(event_id)

    def clear(self):
        self._seen_event_ids.clear()


event_registry = EventRegistry()