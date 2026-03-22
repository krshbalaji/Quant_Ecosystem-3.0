from concurrent.futures import ProcessPoolExecutor
import os


class ParallelWorkerPool:

    pool_type = "process_executor"

    def __init__(self, num_workers=1, **_):

        cpu = os.cpu_count() or 2
        self.num_workers = num_workers if num_workers > 0 else max(1, cpu - 1)
        self.backtest_engine = backtest_engine
        self.metrics_callback = metrics_callback
        # create executor immediately
        self._pool = None
        # keep alias used by our wrapper
        self._executor = None
        self._lock = threading.Lock()
        self._started = False

    def start(self):
        with self._lock:

            if self._pool is not None:
                return

            self._pool = ProcessPoolExecutor(
                max_workers=self.num_workers
            )

            self._executor = self._pool
            self._started = True
        
    def submit(self, fn, *args, **kwargs):
        return self._pool.submit(fn, *args, **kwargs)

    def map(self, fn, items):
        return list(self._pool.map(fn, items))

    def shutdown(self, wait=True):
        self._pool.shutdown(wait=wait)