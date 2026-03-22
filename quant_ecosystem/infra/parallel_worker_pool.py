from concurrent.futures import ProcessPoolExecutor
import os


class ParallelWorkerPool:
    """
    Canonical institutional worker pool.

    Contract:
    - _pool ALWAYS exists after __init__
    - start() is idempotent
    - submit() always safe
    """

    pool_type = "process_executor"

    def __init__(self, num_workers=1, **_):
        cpu = os.cpu_count() or 2
        self.num_workers = num_workers if num_workers > 0 else max(1, cpu - 1)

        # ⭐ CRITICAL — create pool immediately
        self._pool = ProcessPoolExecutor(max_workers=self.num_workers)

        # alias used by other engines
        self._executor = self._pool

    def start(self):
        # lifecycle compatibility — nothing to do
        return

    def submit(self, fn, *args, **kwargs):
        return self._pool.submit(fn, *args, **kwargs)

    def map(self, fn, items):
        return list(self._pool.map(fn, items))

    def shutdown(self, wait=True):
        self._pool.shutdown(wait=wait)