import time


class ExecutionTimeoutGovernor:
    """
    Deterministic execution deadline governance.
    """

    DEFAULT_TIMEOUT = 15

    def __init__(
        self,
        timeout_seconds=None,
    ):
        self.timeout_seconds = (
            timeout_seconds
            or self.DEFAULT_TIMEOUT
        )

    def start_deadline(self):
        return time.time()

    def expired(
        self,
        started_at,
    ):
        return (
            time.time() - started_at
        ) > self.timeout_seconds