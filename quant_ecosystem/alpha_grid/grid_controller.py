"""Grid controller for distributed Alpha Grid."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from quant_ecosystem.alpha_grid.result_aggregator import ResultAggregator
from quant_ecosystem.alpha_grid.task_dispatcher import TaskDispatcher
from quant_ecosystem.alpha_grid.task_queue import GridTask, GridTaskQueue
from quant_ecosystem.alpha_grid.worker_node import WorkerNode


class AlphaGridController:
    """Coordinates workers, tasks, dispatching, and result aggregation."""

    def __init__(
        self,
        task_queue: GridTaskQueue | None = None,
        result_aggregator: ResultAggregator | None = None,
        max_parallel_dispatch: int = 64, **kwargs
    ):
        self.task_queue = task_queue or GridTaskQueue()
        self.result_aggregator = result_aggregator or ResultAggregator()
        self.dispatcher = TaskDispatcher(
            task_queue=self.task_queue,
            result_aggregator=self.result_aggregator,
            max_parallel_dispatch=max_parallel_dispatch,
        )
        self._workers: Dict[str, WorkerNode] = {}

    def register_worker(self, worker: WorkerNode) -> Dict[str, Any]:
        self._workers[worker.node_id] = worker
        self.dispatcher.register_worker(worker)
        return {"registered": worker.node_id, "workers": len(self._workers)}

    def unregister_worker(self, node_id: str) -> Dict[str, Any]:
        node = str(node_id)
        self._workers.pop(node, None)
        self.dispatcher.unregister_worker(node)
        return {"unregistered": node, "workers": len(self._workers)}

    def start(self) -> None:
        self.dispatcher.start()

    def stop(self) -> None:
        self.dispatcher.stop()

    def submit_task(self, task_type: str, payload: Dict, priority: int = 50, max_retries: int = 2) -> str:
        task = GridTask(
            task_type=str(task_type).upper(),
            payload=dict(payload or {}),
            priority=int(priority),
            max_retries=int(max_retries),
        )
        return self.task_queue.put(task)

    def submit_bulk(self, tasks: Iterable[Dict]) -> List[str]:
        ids = []
        for row in list(tasks or []):
            tid = self.submit_task(
                task_type=row.get("task_type", ""),
                payload=row.get("payload", {}),
                priority=int(row.get("priority", 50)),
                max_retries=int(row.get("max_retries", 2)),
            )
            ids.append(tid)
        return ids

    def status(self) -> Dict[str, Any]:
        return {
            "workers": {node_id: worker.health() for node_id, worker in self._workers.items()},
            "queue": self.task_queue.stats(),
            "results": self.result_aggregator.stats(),
        }

    def result(self, task_id: str) -> Dict[str, Any] | None:
        return self.result_aggregator.task_result(task_id)

    def recent_results(self, limit: int = 200) -> List[Dict[str, Any]]:
        return self.result_aggregator.latest(limit=limit)

class ResearchGrid:

    def __init__(self, router):
        self.router = router
        self.workers = []

    def start(self, n_workers=4):

        for i in range(n_workers):
            worker = ResearchWorker(self.router)
            worker.start()
            self.workers.append(worker)