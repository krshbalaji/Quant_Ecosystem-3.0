class TemporalMemory:

    def __init__(self):

        self._events = []

    def record(
        self,
        event,
    ):

        self._events.append(
            event
        )

        self._events = (
            self._events[-5000:]
        )

    def latest(self):

        if not self._events:
            return None

        return (
            self._events[-1]
        )

    def history(self):

        return list(
            self._events
        )


temporal_memory = (
    TemporalMemory()
)