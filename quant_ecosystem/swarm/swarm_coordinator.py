from quant_ecosystem.swarm.execution_shard import (
    ExecutionShard,
)


class SwarmCoordinator:

    def __init__(self):

        self._shards = [
            ExecutionShard(
                shard_id="SHARD-1"
            ),
            ExecutionShard(
                shard_id="SHARD-2"
            ),
            ExecutionShard(
                shard_id="SHARD-3"
            ),
        ]

    def optimal_shard(self):

        return min(
            self._shards,
            key=lambda x: (
                x.queue_depth
            ),
        )

    def assign(self):

        shard = (
            self.optimal_shard()
        )

        shard.assign()

        return shard

    def release(
        self,
        shard,
    ):

        shard.release()


swarm_coordinator = (
    SwarmCoordinator()
)