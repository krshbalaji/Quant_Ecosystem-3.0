class RegimeMemory:

    def __init__(self):

        self._snapshots = []

    def record(
        self,
        snapshot,
    ):

        self._snapshots.append(
            snapshot
        )

        self._snapshots = (
            self._snapshots[-2000:]
        )

    def latest(self):

        if not self._snapshots:
            return None

        return (
            self._snapshots[-1]
        )


regime_memory = (
    RegimeMemory()
)