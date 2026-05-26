class ExecutionAudit:

    def __init__(self):
        self._events = []

    def record(
        self,
        event_name,
        payload,
    ):
        self._events.append(
            {
                "event_name": event_name,
                "payload": payload,
            }
        )

    def all_events(self):
        return list(self._events)

    def clear(self):
        self._events.clear()