"""Task queue for distributed Alpha Grid jobs."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import PriorityQueue, Empty
from typing import Any, Dict, Optional


@dataclass(order=True)
class _PrioritizedTask:
    priority: int
    created_ts: float
    task: "GridTask" = field(compare=False)


@dataclass
class GridTask:
    """A research task to be executed by a worker node."""

    task_type: str
    payload: Dict[str, Any]
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    priority: int = 50
    retries: int = 0
    max_retries: int = 2
    created_ts: float = field(default_factory=time.time)
    assigned_worker: str = ""
    status: str = "QUEUED"


class GridTaskQueue:
    """Thread-safe prioritized task queue."""

    def __init__(self, maxsize: int = 50000, **kwargs):
        self._queue: PriorityQueue = PriorityQueue(maxsize=maxsize)
        self._lock = threading.Lock()
        self._tasks_by_id: Dict[str, GridTask] = {}

    def put(self, task: GridTask) -> str:
        with self._lock:
            self._tasks_by_id[task.task_id] = task
            task.status = "QUEUED"
            self._queue.put(_PrioritizedTask(priority=int(task.priority), created_ts=task.created_ts, task=task))
        return task.task_id

    def get(self, timeout_sec: float = 0.1) -> Optional[GridTask]:
        try:
            wrapped = self._queue.get(timeout=max(0.0, float(timeout_sec)))
        except Empty:
            return None
        task = wrapped.task
        with self._lock:
            task.status = "DISPATCHED"
            self._tasks_by_id[task.task_id] = task
        return task

    def requeue(self, task: GridTask) -> bool:
        with self._lock:
            task.retries += 1
            if task.retries > task.max_retries:
                task.status = "FAILED"
                self._tasks_by_id[task.task_id] = task
                return False
            task.status = "QUEUED"
            self._tasks_by_id[task.task_id] = task
            self._queue.put(_PrioritizedTask(priority=int(task.priority), created_ts=time.time(), task=task))
        return True

    def mark_done(self, task_id: str, status: str = "DONE") -> None:
        with self._lock:
            task = self._tasks_by_id.get(task_id)
            if task:
                task.status = status
                self._tasks_by_id[task_id] = task
            self._queue.task_done()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            queued = self._queue.qsize()
            by_status: Dict[str, int] = {}
            for task in self._tasks_by_id.values():
                by_status[task.status] = by_status.get(task.status, 0) + 1
            by_status["queue_depth"] = queued
            by_status["total_known_tasks"] = len(self._tasks_by_id)
            return by_status

    def get_task(self, task_id: str) -> Optional[GridTask]:
        with self._lock:
            task = self._tasks_by_id.get(task_id)
            return task

