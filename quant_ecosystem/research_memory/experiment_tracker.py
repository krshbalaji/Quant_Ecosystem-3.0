"""
quant_ecosystem/research_memory/experiment_tracker.py
======================================================
Experiment Tracker — Quant Ecosystem 3.0

Records every research experiment (backtest, paper run, walk-forward test,
Monte Carlo simulation, optimisation pass) with full reproducibility metadata.

Design principles
-----------------
• Every experiment is uniquely identified and can be re-run from its record.
• Inputs (parameters, data range, universe) are stored alongside outputs.
• Experiments are grouped into named Runs (e.g. "ema_family_sweep_march_2026").
• Status transitions: PENDING → RUNNING → COMPLETED | FAILED | CANCELLED.
• Thread-safe write path; concurrent readers never see a partial write.

Storage layout
--------------
    <root>/experiments/
        <run_id>/
            manifest.json          — run-level metadata
            <exp_id>.json          — one experiment record each

Integration points
------------------
• research.backtest_engine          — wrap BacktestEngine.run() with tracker
• research.alpha_evolution_engine   — log each evolution cycle as an experiment
• research.distributed_research_engine — one experiment per worker result
• alpha_memory_store                — tracker writes alpha_id links into AlphaRecord
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


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

class ExperimentStatus:
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"
    CANCELLED = "CANCELLED"


class ExperimentType:
    BACKTEST      = "BACKTEST"
    PAPER         = "PAPER"
    WALK_FORWARD  = "WALK_FORWARD"
    MONTE_CARLO   = "MONTE_CARLO"
    OPTIMISATION  = "OPTIMISATION"
    EVOLUTION     = "EVOLUTION"
    SHADOW        = "SHADOW"
    CUSTOM        = "CUSTOM"


# ---------------------------------------------------------------------------
# Data objects
# ---------------------------------------------------------------------------

@dataclass
class ExperimentRecord:
    """
    Complete record of one research experiment.

    Designed so that given this record, a researcher can deterministically
    reproduce the exact experiment: same code, same data range, same params.
    """

    # --- Identity ---
    exp_id:         str
    run_id:         str
    exp_type:       str                 = ExperimentType.BACKTEST
    strategy_id:    str                 = ""
    strategy_family: str                = ""
    description:    str                 = ""

    # --- Inputs (reproducibility) ---
    parameters:     Dict[str, Any]      = field(default_factory=dict)
    data_range:     Dict[str, str]      = field(default_factory=dict)  # start/end
    universe:       List[str]           = field(default_factory=list)
    regime_context: str                 = "all"
    code_version:   str                 = ""    # git commit hash if available

    # --- Outputs ---
    status:         str                 = ExperimentStatus.PENDING
    results:        Dict[str, Any]      = field(default_factory=dict)
    metrics:        Dict[str, float]    = field(default_factory=dict)
    error:          str                 = ""

    # --- Timing ---
    queued_at:      str                 = ""
    started_at:     str                 = ""
    completed_at:   str                 = ""
    duration_sec:   float               = 0.0

    # --- Linkage ---
    parent_exp_id:  Optional[str]       = None  # spawned from another experiment
    child_exp_ids:  List[str]           = field(default_factory=list)
    alpha_id:       Optional[str]       = None  # links to AlphaMemoryStore

    # --- Tags ---
    tags:           List[str]           = field(default_factory=list)
    notes:          str                 = ""

    def is_terminal(self) -> bool:
        return self.status in {
            ExperimentStatus.COMPLETED,
            ExperimentStatus.FAILED,
            ExperimentStatus.CANCELLED,
        }

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "ExperimentRecord":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class RunManifest:
    """
    Groups a set of related experiments into a named research Run.
    E.g. "ema_family_march_sweep", "regime_study_q1_2026".
    """

    run_id:         str
    name:           str             = ""
    description:    str             = ""
    objective:      str             = ""    # what this run set out to answer
    created_at:     str             = ""
    closed_at:      str             = ""
    status:         str             = "open"    # open | closed
    exp_ids:        List[str]       = field(default_factory=list)
    tags:           List[str]       = field(default_factory=list)
    summary:        Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "RunManifest":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# ExperimentTracker
# ---------------------------------------------------------------------------

_NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ExperimentTracker:
    """
    Persistent, thread-safe experiment tracking system.

    Quick-start
    -----------
        tracker = ExperimentTracker(root="data/experiments")

        # Open a research run
        run_id = tracker.open_run("ema_family_sweep", objective="Find best EMA params for trending regime")

        # Log an experiment
        exp = tracker.create_experiment(
            run_id     = run_id,
            exp_type   = ExperimentType.BACKTEST,
            strategy_id = "ema_trend_015",
            parameters  = {"fast": 10, "slow": 30, "atr_filter": True},
            universe    = ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ"],
            data_range  = {"start": "2023-01-01", "end": "2025-12-31"},
        )

        # Mark it running
        tracker.start(exp.exp_id)

        # ... run the actual backtest ...

        # Record results
        tracker.complete(exp.exp_id, metrics={"sharpe": 1.94, "drawdown": -7.2})

        # Close the run with a summary
        tracker.close_run(run_id, summary={"best_sharpe": 1.94, "total_experiments": 12})
    """

    def __init__(
        self,
        root:   str  = "data/experiments",
        config: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        if config and isinstance(config, dict):
            root = config.get("EXPERIMENT_ROOT", root)

        self._root  = Path(root)
        self._lock  = threading.RLock()

        # In-memory caches
        self._runs:  Dict[str, RunManifest]       = {}
        self._exps:  Dict[str, ExperimentRecord]  = {}

        self._root.mkdir(parents=True, exist_ok=True)
        self._rebuild_cache()

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def open_run(
        self,
        name:        str,
        description: str = "",
        objective:   str = "",
        tags:        Optional[List[str]] = None,
    ) -> str:
        """Create a new research run. Returns run_id."""
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        manifest = RunManifest(
            run_id      = run_id,
            name        = name,
            description = description,
            objective   = objective,
            created_at  = _NOW(),
            tags        = tags or [],
        )
        with self._lock:
            self._runs[run_id] = manifest
            run_dir = self._root / run_id
            run_dir.mkdir(exist_ok=True)
            self._write_manifest(manifest)
        return run_id

    def close_run(
        self,
        run_id:  str,
        summary: Optional[Dict] = None,
    ) -> Optional[RunManifest]:
        """Close a run, optionally attaching a summary dict."""
        with self._lock:
            manifest = self._runs.get(run_id)
            if manifest is None:
                return None
            manifest.status   = "closed"
            manifest.closed_at = _NOW()
            if summary:
                manifest.summary.update(summary)
            self._write_manifest(manifest)
            return manifest

    def get_run(self, run_id: str) -> Optional[RunManifest]:
        return self._runs.get(run_id)

    def list_runs(self, status: Optional[str] = None) -> List[RunManifest]:
        runs = list(self._runs.values())
        if status:
            runs = [r for r in runs if r.status == status]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Experiment lifecycle
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        run_id:          str,
        exp_type:        str                     = ExperimentType.BACKTEST,
        strategy_id:     str                     = "",
        strategy_family: str                     = "",
        description:     str                     = "",
        parameters:      Optional[Dict]          = None,
        data_range:      Optional[Dict[str, str]] = None,
        universe:        Optional[List[str]]     = None,
        regime_context:  str                     = "all",
        parent_exp_id:   Optional[str]           = None,
        tags:            Optional[List[str]]     = None,
    ) -> ExperimentRecord:
        """Create and persist a PENDING experiment record. Returns ExperimentRecord."""
        exp_id = f"exp_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        exp = ExperimentRecord(
            exp_id          = exp_id,
            run_id          = run_id,
            exp_type        = exp_type,
            strategy_id     = strategy_id,
            strategy_family = strategy_family,
            description     = description,
            parameters      = parameters or {},
            data_range      = data_range or {},
            universe        = universe or [],
            regime_context  = regime_context,
            parent_exp_id   = parent_exp_id,
            queued_at       = _NOW(),
            tags            = tags or [],
            code_version    = self._git_hash(),
        )
        with self._lock:
            self._exps[exp_id] = exp
            manifest = self._runs.get(run_id)
            if manifest and exp_id not in manifest.exp_ids:
                manifest.exp_ids.append(exp_id)
                self._write_manifest(manifest)
            self._write_experiment(exp)
            # Link parent ↔ child
            if parent_exp_id:
                parent = self._exps.get(parent_exp_id)
                if parent and exp_id not in parent.child_exp_ids:
                    parent.child_exp_ids.append(exp_id)
                    self._write_experiment(parent)
        return exp

    def start(self, exp_id: str) -> Optional[ExperimentRecord]:
        """Transition PENDING → RUNNING. Records started_at timestamp."""
        with self._lock:
            exp = self._exps.get(exp_id)
            if exp is None or exp.is_terminal():
                return exp
            exp.status     = ExperimentStatus.RUNNING
            exp.started_at = _NOW()
            self._write_experiment(exp)
            return exp

    def complete(
        self,
        exp_id:    str,
        metrics:   Optional[Dict[str, float]] = None,
        results:   Optional[Dict[str, Any]]   = None,
        alpha_id:  Optional[str]              = None,
    ) -> Optional[ExperimentRecord]:
        """Transition RUNNING → COMPLETED with metrics and results."""
        with self._lock:
            exp = self._exps.get(exp_id)
            if exp is None:
                return None
            exp.status       = ExperimentStatus.COMPLETED
            exp.completed_at = _NOW()
            exp.metrics      = metrics or {}
            if results:
                exp.results.update(results)
            if alpha_id:
                exp.alpha_id = alpha_id
            exp.duration_sec = self._duration(exp.started_at, exp.completed_at)
            self._write_experiment(exp)
            return exp

    def fail(self, exp_id: str, error: str = "") -> Optional[ExperimentRecord]:
        """Transition → FAILED."""
        with self._lock:
            exp = self._exps.get(exp_id)
            if exp is None:
                return None
            exp.status       = ExperimentStatus.FAILED
            exp.completed_at = _NOW()
            exp.error        = error
            exp.duration_sec = self._duration(exp.started_at, exp.completed_at)
            self._write_experiment(exp)
            return exp

    def cancel(self, exp_id: str) -> Optional[ExperimentRecord]:
        """Transition → CANCELLED."""
        with self._lock:
            exp = self._exps.get(exp_id)
            if exp is None:
                return None
            exp.status       = ExperimentStatus.CANCELLED
            exp.completed_at = _NOW()
            self._write_experiment(exp)
            return exp

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_experiment(self, exp_id: str) -> Optional[ExperimentRecord]:
        return self._exps.get(exp_id)

    def experiments_in_run(self, run_id: str) -> List[ExperimentRecord]:
        return [e for e in self._exps.values() if e.run_id == run_id]

    def experiments_for_strategy(self, strategy_id: str) -> List[ExperimentRecord]:
        return sorted(
            [e for e in self._exps.values() if e.strategy_id == strategy_id],
            key=lambda e: e.queued_at,
        )

    def best_experiment(
        self,
        run_id: Optional[str]     = None,
        strategy_id: Optional[str] = None,
        metric: str               = "sharpe",
    ) -> Optional[ExperimentRecord]:
        pool = list(self._exps.values())
        if run_id:
            pool = [e for e in pool if e.run_id == run_id]
        if strategy_id:
            pool = [e for e in pool if e.strategy_id == strategy_id]
        pool = [e for e in pool if e.status == ExperimentStatus.COMPLETED]
        if not pool:
            return None
        return max(pool, key=lambda e: e.metrics.get(metric, float("-inf")))

    def run_summary(self, run_id: str) -> Dict[str, Any]:
        exps      = self.experiments_in_run(run_id)
        completed = [e for e in exps if e.status == ExperimentStatus.COMPLETED]
        failed    = [e for e in exps if e.status == ExperimentStatus.FAILED]
        sharpes   = [e.metrics.get("sharpe", 0) for e in completed]
        return {
            "run_id":          run_id,
            "total":           len(exps),
            "completed":       len(completed),
            "failed":          len(failed),
            "avg_sharpe":      round(sum(sharpes) / len(sharpes), 4) if sharpes else 0.0,
            "best_sharpe":     round(max(sharpes), 4) if sharpes else 0.0,
            "total_duration_sec": sum(e.duration_sec for e in completed),
        }

    # ------------------------------------------------------------------
    # Context-manager helper for wrapping existing backtest calls
    # ------------------------------------------------------------------

    def track(
        self,
        run_id:      str,
        strategy_id: str = "",
        exp_type:    str = ExperimentType.BACKTEST,
        parameters:  Optional[Dict] = None,
        **kwargs,
    ):
        """
        Context manager that automatically starts and completes/fails an experiment.

        Usage::

            with tracker.track(run_id, strategy_id="ema_trend_015",
                               parameters={"fast": 10}) as exp:
                result = backtest_engine.run(strategy)
                exp.results["raw"] = result   # attach raw output
        """
        return _ExperimentContext(self, run_id, strategy_id, exp_type, parameters or {}, kwargs)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_experiment(self, exp: ExperimentRecord) -> None:
        run_dir = self._root / exp.run_id
        run_dir.mkdir(exist_ok=True)
        path = run_dir / f"{exp.exp_id}.json"
        tmp  = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(exp.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)

    def _write_manifest(self, manifest: RunManifest) -> None:
        path = self._root / manifest.run_id / "manifest.json"
        tmp  = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)

    def _rebuild_cache(self) -> None:
        for run_dir in sorted(self._root.iterdir()):
            if not run_dir.is_dir():
                continue
            manifest_path = run_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    m = RunManifest.from_dict(json.loads(manifest_path.read_text()))
                    self._runs[m.run_id] = m
                except Exception:
                    pass
            for exp_path in sorted(run_dir.glob("exp_*.json")):
                try:
                    e = ExperimentRecord.from_dict(json.loads(exp_path.read_text()))
                    self._exps[e.exp_id] = e
                except Exception:
                    pass

    @staticmethod
    def _duration(start: str, end: str) -> float:
        try:
            import datetime
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            s   = datetime.datetime.strptime(start, fmt)
            e   = datetime.datetime.strptime(end,   fmt)
            return max(0.0, (e - s).total_seconds())
        except Exception:
            return 0.0

    @staticmethod
    def _git_hash() -> str:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=2,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class _ExperimentContext:
    def __init__(self, tracker, run_id, strategy_id, exp_type, parameters, extra):
        self._tracker     = tracker
        self._run_id      = run_id
        self._strategy_id = strategy_id
        self._exp_type    = exp_type
        self._parameters  = parameters
        self._extra       = extra
        self.exp: Optional[ExperimentRecord] = None

    def __enter__(self) -> ExperimentRecord:
        self.exp = self._tracker.create_experiment(
            run_id      = self._run_id,
            strategy_id = self._strategy_id,
            exp_type    = self._exp_type,
            parameters  = self._parameters,
            **{k: v for k, v in self._extra.items()
               if k in ("universe", "data_range", "regime_context", "description", "tags")},
        )
        self._tracker.start(self.exp.exp_id)
        return self.exp

    def __exit__(self, exc_type, exc_val, _tb):
        if self.exp is None:
            return False
        if exc_type is None:
            self._tracker.complete(
                self.exp.exp_id,
                metrics = self.exp.metrics,
                results = self.exp.results,
            )
        else:
            self._tracker.fail(self.exp.exp_id, error=str(exc_val))
        return False   # do not suppress exceptions
