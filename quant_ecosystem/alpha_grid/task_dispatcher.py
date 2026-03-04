"""Task dispatcher for Alpha Grid."""

from __future__ import annotations

import threading
import time
from typing import Dict


class TaskDispatcher:
    """Dispatches queued tasks to available workers using worker threads."""

    def __init__(self, task_queue, result_aggregator, max_parallel_dispatch: int = 64):
        self.task_queue = task_queue
        self.result_aggregator = result_aggregator
        self.max_parallel_dispatch = max(1, int(max_parallel_dispatch))
        self._workers: Dict[str, object] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._running = False

    def register_worker(self, worker) -> None:
        self._workers[str(worker.node_id)] = worker

    def unregister_worker(self, node_id: str) -> None:
        self._workers.pop(str(node_id), None)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for node_id in list(self._workers.keys())[: self.max_parallel_dispatch]:
            if node_id in self._threads and self._threads[node_id].is_alive():
                continue
            thread = threading.Thread(target=self._worker_loop, args=(node_id,), daemon=True)
            self._threads[node_id] = thread
            thread.start()

    def stop(self) -> None:
        self._running = False

    def _worker_loop(self, node_id: str) -> None:
        worker = self._workers.get(node_id)
        if worker is None:
            return
        while self._running:
            task = self.task_queue.get(timeout_sec=0.2)
            if task is None:
                time.sleep(0.02)
                continue
            task.assigned_worker = node_id
            result = worker.execute(task.task_type, task.payload)
            result["task_id"] = task.task_id
            result["assigned_worker"] = node_id
            self.result_aggregator.accept(result)
            if result.get("ok"):
                self.task_queue.mark_done(task.task_id, status="DONE")
            else:
                retried = self.task_queue.requeue(task)
                if not retried:
                    self.task_queue.mark_done(task.task_id, status="FAILED")

