from concurrent.futures import ProcessPoolExecutor
import os


class ParallelWorkerPool:

    pool_type = "process_executor"

    def __init__(self, num_workers=1, **_):

        cpu = os.cpu_count() or 2
        self.n_workers = num_workers if num_workers > 0 else max(1, cpu - 1)

        self._executor = None
        self._pool = None      # ⭐ legacy contract
        self._started = False

    # -----------------------------------------------------

    def start(self):

        if self._started:
            return

        self._executor = ProcessPoolExecutor(
            max_workers=self.n_workers
        )

        # ⭐ expose legacy handle expected by GridScheduler
        self._pool = self._executor

        self._started = True

    # -----------------------------------------------------

    def submit(self, fn, *args, **kwargs):

        if not self._started:
            self.start()

        return self._executor.submit(fn, *args, **kwargs)

    # -----------------------------------------------------

    def map(self, fn, items):

        if not self._started:
            self.start()

        return list(self._executor.map(fn, items))

    # -----------------------------------------------------

    def shutdown(self, wait=True):

        if self._executor:
            self._executor.shutdown(wait=wait)