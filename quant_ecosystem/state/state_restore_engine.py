from quant_ecosystem.state.state_manager import (
    state_manager,
)


class StateRestoreEngine:

    def restore(
        self,
        snapshot,
    ):
        state_manager.restore(
            snapshot
        )
        return True


state_restore_engine = (
    StateRestoreEngine()
)