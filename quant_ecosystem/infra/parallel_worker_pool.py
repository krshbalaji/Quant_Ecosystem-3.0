from concurrent.futures import ProcessPoolExecutor
import os
import threading


class ParallelWorkerPool:
    """
    Canonical institutional worker pool.

    Contract:
    - _pool ALWAYS exists after __init__
    - start() is idempotent
    - submit() always safe
    - active_count() reflects real inflight futures
    """

    pool_type = "process_executor"

    def __init__(self, num_workers=1, **_):
        cpu = os.cpu_count() or 2
        self.num_workers = num_workers if num_workers > 0 else max(1, cpu - 1)

        self._pool = ProcessPoolExecutor(max_workers=self.num_workers)
        self._executor = self._pool

        # ⭐ institutional inflight tracking
        self._futures = {}
        self._lock = threading.Lock()

    def start(self):
        return

    def submit(self, fn, *args, **kwargs):
        fut = self._pool.submit(fn, *args, **kwargs)

        with self._lock:
            self._futures[id(fut)] = fut

        def _done(_):
            with self._lock:
                self._futures.pop(id(fut), None)

        fut.add_done_callback(_done)

        return fut

    def map(self, fn, items):
        return list(self._pool.map(fn, items))

    def shutdown(self, wait=True):
        self._pool.shutdown(wait=wait)

    def active_count(self) -> int:
        with self._lock:
            return len(self._futures)