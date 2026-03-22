from concurrent.futures import ProcessPoolExecutor
import os


class ParallelWorkerPool:

    pool_type = "process_executor"

    def __init__(self, num_workers=1, **_):

        cpu = os.cpu_count() or 2
        self.n_workers = num_workers if num_workers > 0 else max(1, cpu - 1)

        # create executor immediately
        self._pool = ProcessPoolExecutor(max_workers=self.n_workers)

        # keep alias used by our wrapper
        self._executor = self._pool

        self._started = True

    def start(self):
        # compatibility with grid lifecycle
        return

    def submit(self, fn, *args, **kwargs):
        return self._pool.submit(fn, *args, **kwargs)

    def map(self, fn, items):
        return list(self._pool.map(fn, items))

    def shutdown(self, wait=True):
        self._pool.shutdown(wait=wait)