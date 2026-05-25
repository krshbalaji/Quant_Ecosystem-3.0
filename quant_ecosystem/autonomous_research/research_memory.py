class ResearchMemory:

    def __init__(self):
        self._memory = {}

    def record(
        self,
        signal_id,
        confidence,
        outcome=None,
    ):
        self._memory[signal_id] = {
            "confidence": confidence,
            "outcome": outcome,
        }

    def fetch(
        self,
        signal_id,
    ):
        return self._memory.get(
            signal_id
        )

    def clear(self):
        self._memory.clear()


research_memory = (
    ResearchMemory()
)