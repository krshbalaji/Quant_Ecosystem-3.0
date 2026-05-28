from quant_ecosystem.execution.mesh.node_identity import (
    node_identity,
)

from quant_ecosystem.execution.mesh.node_registry import (
    node_registry,
)

from quant_ecosystem.execution.mesh.execution_lease import (
    execution_lease,
)


class MeshCoordinator:

    def heartbeat(self):

        node_registry.heartbeat(
            node_identity.node_id
        )

    def acquire_execution(
        self,
        execution_key,
    ):

        return (
            execution_lease.acquire(
                execution_key,
                node_identity.node_id,
            )
        )

    def release_execution(
        self,
        execution_key,
    ):

        execution_lease.release(
            execution_key,
            node_identity.node_id,
        )

    def active_nodes(self):

        return (
            node_registry
            .active_nodes()
        )


mesh_coordinator = (
    MeshCoordinator()
)