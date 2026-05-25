from quant_ecosystem.persistence.durable_snapshot_repository import (
    durable_snapshot_repository,
)


class RecoveryManager:

    def recover(
        self,
        snapshot_name,
    ):
        return durable_snapshot_repository.load(
            snapshot_name
        )


recovery_manager = RecoveryManager()