class LearningMemory:

    def __init__(self):

        self._events = []

    def record(
        self,
        payload,
    ):

        self._events.append(
            payload
        )

        self._events = (
            self._events[-5000:]
        )

    def events(self):

        return list(
            self._events
        )


learning_memory = (
    LearningMemory()
)