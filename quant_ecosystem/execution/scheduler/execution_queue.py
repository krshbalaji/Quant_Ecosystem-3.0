import heapq
import time


class ExecutionQueue:

    def __init__(self):

        self._queue = []

    def schedule(
        self,
        execute_at,
        payload,
    ):

        heapq.heappush(
            self._queue,
            (
                execute_at,
                payload,
            ),
        )

    def ready(self):

        now = time.time()

        ready = []

        while self._queue:

            execute_at, payload = (
                self._queue[0]
            )

            if execute_at > now:
                break

            heapq.heappop(
                self._queue
            )

            ready.append(payload)

        return ready


execution_queue = (
    ExecutionQueue()
)