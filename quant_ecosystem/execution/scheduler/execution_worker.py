from quant_ecosystem.execution.mesh.mesh_coordinator import (
    mesh_coordinator,
)

from quant_ecosystem.execution.scheduler.autonomous_scheduler import (
    autonomous_scheduler,
)


class ExecutionWorker:

    def poll(self):

        mesh_coordinator.heartbeat()

        ready = (
            autonomous_scheduler.poll()
        )

        owned = []

        for payload in ready:

            execution_key = str(
                payload.get(
                    "execution_key",
                    ""
                )
            )

            acquired = (
                mesh_coordinator
                .acquire_execution(
                    execution_key
                )
            )

            if acquired:
                owned.append(payload)

        return owned


execution_worker = (
    ExecutionWorker()
)