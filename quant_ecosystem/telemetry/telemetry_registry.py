class TelemetryRegistry:

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
            self._snapshots[-1000:]
        )

    def latest(self):

        if not self._snapshots:
            return None

        return (
            self._snapshots[-1]
        )

    def all(self):

        return list(
            self._snapshots
        )


telemetry_registry = (
    TelemetryRegistry()
)