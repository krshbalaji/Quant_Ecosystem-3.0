from quant_ecosystem.swarm.swarm_coordinator import (
    swarm_coordinator,
)


class WorkloadBalancer:

    def allocate(self):

        return (
            swarm_coordinator
            .assign()
        )

    def complete(
        self,
        shard,
    ):

        swarm_coordinator.release(
            shard
        )


workload_balancer = (
    WorkloadBalancer()
)