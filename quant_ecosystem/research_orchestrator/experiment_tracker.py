"""
experiment_tracker.py
MLflow-style experiment tracker for the quant research pipeline.
Tracks every research run: genome generation, backtests, signal evaluations,
parameter sweeps, and promotion decisions — with full lineage.
Persisted to JSON lines for zero-dependency operation.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_TRACKING_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "experiments"
_TRACKING_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass
class Run:
    """One experiment run."""
    run_id: str
    experiment_name: str
    run_type: str           # GENOME_EVAL | BACKTEST | SIGNAL_EVAL | PARAM_SWEEP | PROMOTION
    status: str             # RUNNING | COMPLETED | FAILED
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)  # file paths
    parent_run_id: Optional[str] = None
    genome_id: Optional[str] = None
    strategy_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_sec: Optional[float] = None
    error: Optional[str] = None

    def complete(self, metrics: Optional[Dict[str, float]] = None) -> None:
        self.status = "COMPLETED"
        self.end_time = time.time()
        self.duration_sec = round(self.end_time - self.start_time, 4)
        if metrics:
            self.metrics.update(metrics)

    def fail(self, error: str) -> None:
        self.status = "FAILED"
        self.end_time = time.time()
        self.duration_sec = round(self.end_time - self.start_time, 4)
        self.error = str(error)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class ExperimentTracker:
    """
    Thread-safe experiment tracker.

    Usage:
        tracker = ExperimentTracker()
        run_id = tracker.start_run("genome_evolution", "GENOME_EVAL",
                                   params={"population_size": 50})
        tracker.log_metric(run_id, "sharpe", 1.84)
        tracker.end_run(run_id, metrics={"fitness": 0.72})

    Query:
        runs = tracker.query(experiment_name="genome_evolution", min_sharpe=1.5)
        best = tracker.best_run("genome_evolution", metric="sharpe")
    """

    def __init__(
        self,
        tracking_root: Optional[Path] = None,
        max_runs_in_memory: int = 10000,
    ) -> None:
        self._root = tracking_root or _TRACKING_ROOT
        self._runs: Dict[str, Run] = {}
        self._lock = threading.Lock()
        self._max_mem = int(max_runs_in_memory)
        self._load_recent()

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(
        self,
        experiment_name: str,
        run_type: str = "BACKTEST",
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        parent_run_id: Optional[str] = None,
        genome_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
    ) -> str:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        run = Run(
            run_id=run_id,
            experiment_name=str(experiment_name),
            run_type=str(run_type).upper(),
            status="RUNNING",
            params=dict(params or {}),
            tags=dict(tags or {}),
            parent_run_id=parent_run_id,
            genome_id=genome_id,
            strategy_id=strategy_id,
        )
        with self._lock:
            self._runs[run_id] = run
        return run_id

    def log_param(self, run_id: str, key: str, value: Any) -> None:
        run = self._runs.get(run_id)
        if run:
            run.params[str(key)] = value

    def log_params(self, run_id: str, params: Dict[str, Any]) -> None:
        run = self._runs.get(run_id)
        if run:
            run.params.update(params)

    def log_metric(self, run_id: str, key: str, value: float) -> None:
        run = self._runs.get(run_id)
        if run:
            run.metrics[str(key)] = float(value)

    def log_metrics(self, run_id: str, metrics: Dict[str, float]) -> None:
        run = self._runs.get(run_id)
        if run:
            run.metrics.update({k: float(v) for k, v in metrics.items()})

    def set_tag(self, run_id: str, key: str, value: str) -> None:
        run = self._runs.get(run_id)
        if run:
            run.tags[str(key)] = str(value)

    def end_run(
        self,
        run_id: str,
        metrics: Optional[Dict[str, float]] = None,
        status: str = "COMPLETED",
    ) -> Optional[Run]:
        run = self._runs.get(run_id)
        if run is None:
            return None
        if status == "FAILED":
            run.fail(str(metrics.get("error", "unknown")) if metrics else "unknown")
        else:
            run.complete(metrics)
        self._persist(run)
        return run

    def fail_run(self, run_id: str, error: str) -> None:
        run = self._runs.get(run_id)
        if run:
            run.fail(error)
            self._persist(run)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> Optional[Run]:
        return self._runs.get(run_id)

    def query(
        self,
        experiment_name: Optional[str] = None,
        run_type: Optional[str] = None,
        status: Optional[str] = None,
        min_sharpe: Optional[float] = None,
        min_fitness: Optional[float] = None,
        genome_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Run]:
        runs = list(self._runs.values())
        if experiment_name:
            runs = [r for r in runs if r.experiment_name == experiment_name]
        if run_type:
            runs = [r for r in runs if r.run_type == run_type.upper()]
        if status:
            runs = [r for r in runs if r.status == status.upper()]
        if min_sharpe is not None:
            runs = [r for r in runs if r.metrics.get("sharpe", 0.0) >= min_sharpe]
        if min_fitness is not None:
            runs = [r for r in runs if r.metrics.get("fitness", r.metrics.get("fitness_score", 0.0)) >= min_fitness]
        if genome_id:
            runs = [r for r in runs if r.genome_id == genome_id]
        if strategy_id:
            runs = [r for r in runs if r.strategy_id == strategy_id]
        # Sort by start time, most recent first
        runs.sort(key=lambda r: r.start_time, reverse=True)
        return runs[:limit]

    def best_run(
        self,
        experiment_name: str,
        metric: str = "sharpe",
        run_type: Optional[str] = None,
    ) -> Optional[Run]:
        candidates = self.query(experiment_name=experiment_name, run_type=run_type,
                                status="COMPLETED", limit=5000)
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.metrics.get(metric, float("-inf")))

    def run_history(self, experiment_name: str, metric: str = "sharpe") -> List[float]:
        """Time-ordered list of a metric for a given experiment."""
        runs = self.query(experiment_name=experiment_name, status="COMPLETED", limit=5000)
        runs.sort(key=lambda r: r.start_time)
        return [r.metrics.get(metric, 0.0) for r in runs]

    def experiment_summary(self, experiment_name: str) -> Dict[str, Any]:
        runs = self.query(experiment_name=experiment_name, limit=10000)
        completed = [r for r in runs if r.status == "COMPLETED"]
        if not completed:
            return {"experiment_name": experiment_name, "total_runs": len(runs), "completed": 0}
        sharpes = [r.metrics.get("sharpe", 0.0) for r in completed]
        return {
            "experiment_name": experiment_name,
            "total_runs": len(runs),
            "completed": len(completed),
            "failed": sum(1 for r in runs if r.status == "FAILED"),
            "best_sharpe": round(max(sharpes), 4),
            "avg_sharpe": round(float(sum(sharpes) / len(sharpes)), 4),
            "best_run_id": (max(completed, key=lambda r: r.metrics.get("sharpe", 0.0))).run_id,
        }

    def list_experiments(self) -> List[str]:
        return sorted({r.experiment_name for r in self._runs.values()})

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, run: Run) -> None:
        path = self._root / f"{run.experiment_name}.jsonl"
        try:
            with open(path, "a") as f:
                f.write(json.dumps(run.to_dict()) + "\n")
        except Exception:
            pass

    def _load_recent(self, max_per_experiment: int = 2000) -> None:
        try:
            for path in self._root.glob("*.jsonl"):
                lines = []
                with open(path) as f:
                    lines = f.readlines()
                for line in lines[-max_per_experiment:]:
                    try:
                        d = json.loads(line.strip())
                        run = Run(**{k: d[k] for k in Run.__dataclass_fields__ if k in d})
                        self._runs[run.run_id] = run
                    except Exception:
                        continue
        except Exception:
            pass

    def flush(self) -> None:
        """Persist all in-memory completed runs that haven't been written yet."""
        for run in self._runs.values():
            if run.status in ("COMPLETED", "FAILED"):
                self._persist(run)
