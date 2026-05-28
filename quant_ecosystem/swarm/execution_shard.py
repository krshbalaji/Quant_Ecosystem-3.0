class ExecutionShard:

    def __init__(
        self,
        shard_id,
    ):

        self.shard_id = shard_id

        self.queue_depth = 0

    def assign(self):

        self.queue_depth += 1

    def release(self):

        self.queue_depth = max(
            0,
            self.queue_depth - 1,
        )