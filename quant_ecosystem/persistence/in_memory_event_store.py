class InMemoryEventStore:

    def __init__(self):
        self._events = []

    def append(
        self,
        event_type,
        payload,
    ):
        self._events.append(
            {
                "event_type": event_type,
                "payload": payload,
            }
        )

    def all_events(self):
        return list(self._events)

    def by_type(
        self,
        event_type,
    ):
        return [
            e for e in self._events
            if e["event_type"] == event_type
        ]

    def clear(self):
        self._events.clear()


event_store = InMemoryEventStore()