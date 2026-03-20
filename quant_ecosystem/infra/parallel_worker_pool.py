from concurrent.futures import ProcessPoolExecutor
import os


class ParallelWorkerPool:
    """
    Institutional CPU parallel execution pool
    Clean contract for ResearchGrid / GridScheduler
    """

    pool_type = "process"

    def __init__(self, num_workers=1, **kwargs):

        cpu = os.cpu_count() or 2
        self.n_workers = num_workers if num_workers > 0 else max(1, cpu - 1)

        self._pool = None
        self._started = False

    # -------------------------------------------------

    def start(self):

        if self._started:
            return

        self._pool = ProcessPoolExecutor(
            max_workers=self.n_workers
        )

        self._started = True

    # -------------------------------------------------

    def submit(self, fn, *args, **kwargs):

        if not self._started:
            self.start()

        return self._pool.submit(fn, *args, **kwargs)

    # -------------------------------------------------

    def map(self, fn, items):

        if not self._started:
            self.start()

        futures = [
            self._pool.submit(fn, x)
            for x in items
        ]

        return [f.result() for f in futures]

    # -------------------------------------------------

    def shutdown(self, wait=True):

        if self._pool:
            self._pool.shutdown(wait=wait)

        self._started = False