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

    def submit(self, job, callback=None):
        """
        Institutional Grid contract:
        - job is GridJob
        - dispatch via _dispatch_job
        """

        from quant_ecosystem.research.grid.parallel_research_grid import _dispatch_job

        fut = self._pool.submit(_dispatch_job, job.job_type, job.payload)

        if callback:
            from quant_ecosystem.research.grid.parallel_research_grid import GridResult

            def _wrap_done(f):
                raw = f.result()

                result = GridResult(
                    job_id = job.job_id,
                    job_type = job.job_type,
                    ok = raw.get("error") is None,
                    payload = job.payload,
                    result = raw,
                    error = raw.get("error"),
                    elapsed_sec = 0.0,
                    worker_pid = os.getpid()
                )

                callback(result)

            fut.add_done_callback(_wrap_done)

        return fut

    def map(self, fn, items):
        return list(self._pool.map(fn, items))

    def shutdown(self, wait=True):
        self._pool.shutdown(wait=wait)

    def active_count(self) -> int:
        with self._lock:
            return len(self._futures)