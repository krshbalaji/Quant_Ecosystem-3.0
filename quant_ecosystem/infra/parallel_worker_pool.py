import threading
from queue import Queue


class ParallelWorkerPool:
    """
    Simple institutional-grade local worker pool.
    Executes tasks in parallel threads.
    """

    def __init__(self, num_workers: int = 2):
        self.num_workers = max(1, int(num_workers))
        self._queue = Queue()
        self._workers = []
        self._running = False

    def start(self):
        if self._running:
            return

        self._running = True

        for _ in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self._workers.append(t)

    def submit(self, fn, *args, **kwargs):
        self._queue.put((fn, args, kwargs))

    def _worker_loop(self):
        while self._running:
            fn, args, kwargs = self._queue.get()
            try:
                fn(*args, **kwargs)
            except Exception as e:
                print(f"[ParallelWorkerPool] worker error: {e}")

    def shutdown(self):
        self._running = False