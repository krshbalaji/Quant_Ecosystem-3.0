class DurableSnapshotRepository:

    def __init__(self):
        self._snapshots = {}

    def save_snapshot(
        self,
        name,
        snapshot,
    ):
        self._snapshots[name] = snapshot

    def load_snapshot(
        self,
        name,
    ):
        return self._snapshots.get(name)

    def clear(self):
        self._snapshots.clear()


durable_snapshot_repository = (
    DurableSnapshotRepository()
)