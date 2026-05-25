from quant_ecosystem.state.state_manager import (
    state_manager,
)


class StateSnapshotEngine:

    def capture(self):
        return state_manager.snapshot()


state_snapshot_engine = (
    StateSnapshotEngine()
)