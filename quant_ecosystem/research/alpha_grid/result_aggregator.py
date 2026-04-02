"""Result aggregator for distributed Alpha Grid."""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List


class ResultAggregator:
    """Collects worker results and propagates updates to research modules."""

    def __init__(self, max_results: int = 20000, **kwargs):
        self._lock = threading.Lock()
        self._results: Deque[Dict[str, Any]] = deque(maxlen=max_results)
        self._latest_by_task: Dict[str, Dict[str, Any]] = {}
        self.total_ok = 0
        self.total_failed = 0

    def accept(self, result: Dict[str, Any]) -> None:
        row = dict(result or {})
        row.setdefault("timestamp", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        with self._lock:
            self._results.append(row)
            task_id = str(row.get("task_id", ""))
            if task_id:
                self._latest_by_task[task_id] = row
            if bool(row.get("ok", False)):
                self.total_ok += 1
            else:
                self.total_failed += 1

    def latest(self, limit: int = 200) -> List[Dict[str, Any]]:
        take = max(1, int(limit))
        with self._lock:
            return list(self._results)[-take:]

    def task_result(self, task_id: str) -> Dict[str, Any] | None:
        with self._lock:
            row = self._latest_by_task.get(str(task_id))
            return dict(row) if row else None

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_ok": self.total_ok,
                "total_failed": self.total_failed,
                "buffered_results": len(self._results),
            }

