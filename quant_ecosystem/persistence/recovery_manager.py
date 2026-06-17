from quant_ecosystem.persistence.durable_snapshot_repository import (
    durable_snapshot_repository,
)


class RecoveryManager:

    def recover(
        self,
        snapshot_name,
    ):
        return durable_snapshot_repository.load_snapshot(
            snapshot_name
        )


recovery_manager = RecoveryManager()