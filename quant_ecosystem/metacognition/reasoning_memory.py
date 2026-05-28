class ReasoningMemory:

    def __init__(self):

        self._rationales = []

    def record(
        self,
        rationale,
    ):

        self._rationales.append(
            rationale
        )

        self._rationales = (
            self._rationales[-3000:]
        )

    def latest(self):

        if not self._rationales:
            return None

        return (
            self._rationales[-1]
        )


reasoning_memory = (
    ReasoningMemory()
)