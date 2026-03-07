"""
quant_ecosystem/research_memory/layer.py
=========================================
Research Memory Layer — Unified Façade — Quant Ecosystem 3.0

Single entry point that wires the five research memory sub-systems together
and exposes a clean, high-level API.

Sub-systems
-----------
AlphaMemoryStore      — persistent alpha discovery records
ExperimentTracker     — reproducible experiment logging
StrategyGenealogy     — parent-child evolution tree
PerformanceArchive    — regime-aware performance history
SnapshotStore         — point-in-time research snapshots

Design principles
-----------------
• Lazy initialisation: sub-systems are created only when first accessed.
• All I/O paths are configurable via constructor config dict.
• Boot-safe: all sub-systems degrade gracefully if their data dirs are empty.
• Thread-safe: each sub-system manages its own lock; the layer adds no
  additional coarse locking to avoid deadlocks.

Integration in SystemFactory
-----------------------------
    # In system_factory._boot_research_memory():
    try:
        from quant_ecosystem.research_memory.layer import ResearchMemoryLayer
        router.research_memory = ResearchMemoryLayer(config=self.config)
    except Exception:
        logger.warning("ResearchMemoryLayer unavailable")

After boot, all engines access it as router.research_memory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResearchMemoryLayer:
    """
    Unified research memory façade.

    Configuration keys (all optional, all have defaults):
        RESEARCH_MEMORY_ROOT      base dir (default: "data/research_memory")
        ALPHA_MEMORY_ROOT         override for alpha store
        EXPERIMENT_ROOT           override for experiment tracker
        GENEALOGY_ROOT            override for genealogy
        PERFORMANCE_ARCHIVE_ROOT  override for performance archive
        SNAPSHOT_ROOT             override for snapshot store

    Usage
    -----
        layer = ResearchMemoryLayer(config={"RESEARCH_MEMORY_ROOT": "/opt/quant/data"})

        # Record a new alpha discovery
        alpha = layer.record_alpha({
            "strategy_id": "ema_trend_015",
            "parent_id":   "ema_trend_011",
            "family":      "ema_trend",
            "regime":      "trending",
            "sharpe":      1.94,
            "drawdown":    -7.2,
            "trade_count": 112,
        })

        # Log an experiment
        with layer.track_experiment(run_id, strategy_id="ema_trend_015") as exp:
            result = backtest.run(strategy)
            exp.results["raw"] = result

        # Register strategy genealogy
        layer.register_mutation(
            child_id="ema_trend_015", parent_id="ema_trend_011",
            family="ema_trend", mutation_ops=["tweak_fast_period"],
            birth_sharpe=1.94,
        )

        # Archive performance
        layer.archive_performance({
            "strategy_id": "ema_trend_015",
            "phase":       "backtest",
            "regime":      "trending",
            "sharpe":      1.94,
            "drawdown":    -7.2,
            "trade_count": 112,
        })

        # Take a daily snapshot
        layer.daily_snapshot(label="eod_2026_03_07")

        # Regime-aware strategy selection
        top = layer.top_alphas_for_regime("trending", n=5)
    """

    def __init__(self, config: Optional[Dict] = None, **kwargs) -> None:
        self._config = config or {}
        self._base   = Path(self._config.get("RESEARCH_MEMORY_ROOT", "data/research_memory"))
        self._base.mkdir(parents=True, exist_ok=True)

        # Lazy-loaded sub-systems
        self._alpha_store: Any  = None
        self._tracker:     Any  = None
        self._genealogy:   Any  = None
        self._perf:        Any  = None
        self._snapshots:   Any  = None

        # Default run_id for ad-hoc experiments
        self._default_run_id: Optional[str] = None

        logger.info("[ResearchMemoryLayer] initialised at %s", self._base)

    # ------------------------------------------------------------------
    # Sub-system accessors (lazy initialisation)
    # ------------------------------------------------------------------

    @property
    def alpha_store(self):
        if self._alpha_store is None:
            from quant_ecosystem.research_memory.alpha_memory_store import AlphaMemoryStore
            root = self._config.get("ALPHA_MEMORY_ROOT", str(self._base / "alphas"))
            self._alpha_store = AlphaMemoryStore(root=root)
        return self._alpha_store

    @property
    def tracker(self):
        if self._tracker is None:
            from quant_ecosystem.research_memory.experiment_tracker import ExperimentTracker
            root = self._config.get("EXPERIMENT_ROOT", str(self._base / "experiments"))
            self._tracker = ExperimentTracker(root=root)
        return self._tracker

    @property
    def genealogy(self):
        if self._genealogy is None:
            from quant_ecosystem.research_memory.strategy_genealogy import StrategyGenealogy
            root = self._config.get("GENEALOGY_ROOT", str(self._base / "genealogy"))
            self._genealogy = StrategyGenealogy(root=root)
        return self._genealogy

    @property
    def performance(self):
        if self._perf is None:
            from quant_ecosystem.research_memory.performance_archive import PerformanceArchive
            root = self._config.get("PERFORMANCE_ARCHIVE_ROOT", str(self._base / "performance"))
            self._perf = PerformanceArchive(root=root)
        return self._perf

    @property
    def snapshots(self):
        if self._snapshots is None:
            from quant_ecosystem.research_memory.research_snapshot import SnapshotStore
            root = self._config.get("SNAPSHOT_ROOT", str(self._base / "snapshots"))
            self._snapshots = SnapshotStore(root=root)
        return self._snapshots

    # ------------------------------------------------------------------
    # Alpha API
    # ------------------------------------------------------------------

    def record_alpha(self, record: Dict) -> Any:
        """Record a new alpha discovery from a plain dict."""
        return self.alpha_store.record_from_dict(record)

    def update_alpha_live_stats(
        self,
        strategy_id: str,
        live_sharpe: Optional[float]  = None,
        live_drawdown: Optional[float] = None,
        live_trade_count: Optional[int] = None,
        status: Optional[str]          = None,
    ) -> Any:
        return self.alpha_store.update_live_stats(
            strategy_id,
            live_sharpe      = live_sharpe,
            live_drawdown    = live_drawdown,
            live_trade_count = live_trade_count,
            status           = status,
        )

    def retire_alpha(self, strategy_id: str, reason: str = "") -> Any:
        self.alpha_store.retire(strategy_id, reason=reason)
        self.genealogy.update_status(strategy_id, "retired")
        self.performance.update_status(strategy_id, "retired")

    def top_alphas_for_regime(self, regime: str, n: int = 10) -> List[Any]:
        """Return top N AlphaRecords for a given regime, ranked by composite score."""
        return self.alpha_store.top_alphas(regime=regime, n=n)

    # ------------------------------------------------------------------
    # Experiment API
    # ------------------------------------------------------------------

    def open_run(self, name: str, objective: str = "", **kwargs) -> str:
        """Open a new experiment run. Returns run_id."""
        run_id = self.tracker.open_run(name=name, objective=objective, **kwargs)
        if self._default_run_id is None:
            self._default_run_id = run_id
        return run_id

    def track_experiment(self, run_id: Optional[str] = None, **kwargs):
        """
        Context manager for wrapping a backtest or research step.

        Example::

            with layer.track_experiment(run_id, strategy_id="ema_015",
                                         parameters={"fast": 10}) as exp:
                result = backtest.run(strategy)
        """
        rid = run_id or self._ensure_default_run()
        return self.tracker.track(rid, **kwargs)

    def log_experiment_result(
        self,
        run_id:      str,
        strategy_id: str,
        metrics:     Dict[str, float],
        parameters:  Optional[Dict]  = None,
        regime:      str             = "all",
        exp_type:    str             = "BACKTEST",
    ) -> Any:
        """
        Convenience: create + immediately complete a single experiment.
        Use this when you have results ready and don't need the context manager.
        """
        exp = self.tracker.create_experiment(
            run_id         = run_id,
            strategy_id    = strategy_id,
            exp_type       = exp_type,
            parameters     = parameters or {},
            regime_context = regime,
        )
        self.tracker.start(exp.exp_id)
        return self.tracker.complete(exp.exp_id, metrics=metrics)

    # ------------------------------------------------------------------
    # Genealogy API
    # ------------------------------------------------------------------

    def register_seed(
        self,
        strategy_id:  str,
        family:       str,
        birth_sharpe: float = 0.0,
        birth_regime: str   = "all",
        **kwargs,
    ) -> Any:
        from quant_ecosystem.research_memory.strategy_genealogy import GenealogyNode
        return self.genealogy.register(GenealogyNode(
            strategy_id   = strategy_id,
            family        = family,
            mutation_type = "seed",
            birth_sharpe  = birth_sharpe,
            birth_regime  = birth_regime,
            **{k: v for k, v in kwargs.items() if k in GenealogyNode.__dataclass_fields__},
        ))

    def register_mutation(
        self,
        child_id:        str,
        parent_id:       str,
        family:          str,
        mutation_ops:    Optional[List[str]] = None,
        parameter_delta: Optional[Dict]      = None,
        birth_sharpe:    float               = 0.0,
        birth_drawdown:  float               = 0.0,
        birth_regime:    str                 = "all",
    ) -> Any:
        return self.genealogy.register_mutation(
            child_id        = child_id,
            parent_id       = parent_id,
            family          = family,
            mutation_ops    = mutation_ops,
            parameter_delta = parameter_delta,
            birth_sharpe    = birth_sharpe,
            birth_drawdown  = birth_drawdown,
            birth_regime    = birth_regime,
        )

    def get_lineage(self, strategy_id: str) -> Dict:
        return self.genealogy.lineage_report(strategy_id)

    # ------------------------------------------------------------------
    # Performance API
    # ------------------------------------------------------------------

    def archive_performance(self, record: Dict) -> Any:
        """Archive a performance slice from a plain dict."""
        return self.performance.add_slice_from_dict(record)

    def bridge_performance_store(
        self,
        strategy_id: str,
        metrics:     Dict[str, float],
        phase:       str = "live",
        regime:      str = "all",
    ) -> Any:
        """
        Bridge an existing PerformanceStore.get_metrics() result into the archive.
        Called from strategy_survival or shadow_trading.
        """
        return self.performance.bridge_from_performance_store(
            strategy_id, metrics, phase=phase, regime=regime
        )

    def deterioration_score(self, strategy_id: str) -> float:
        return self.performance.deterioration_score(strategy_id)

    def top_strategies_for_regime(self, regime: str, n: int = 10) -> List[Dict]:
        return self.performance.top_strategies_for_regime(regime=regime, n=n)

    # ------------------------------------------------------------------
    # Snapshot API
    # ------------------------------------------------------------------

    def daily_snapshot(
        self,
        label:       str = "",
        notes:       str = "",
        quant_mode:  str = "PAPER",
        include_experiments: bool = True,
    ) -> Any:
        """Capture a full research state snapshot."""
        return self.snapshots.create(
            alpha_store  = self._alpha_store,     # only pass if already loaded
            genealogy    = self._genealogy,
            perf_archive = self._perf,
            tracker      = self._tracker,
            label        = label or f"snapshot_{__import__('time').strftime('%Y_%m_%d')}",
            trigger      = "scheduled",
            notes        = notes,
            quant_mode   = quant_mode,
            include_experiments = include_experiments,
        )

    def manual_snapshot(self, label: str = "", notes: str = "") -> Any:
        """Take a manual snapshot on demand."""
        return self.snapshots.create(
            alpha_store  = self._alpha_store,
            genealogy    = self._genealogy,
            perf_archive = self._perf,
            tracker      = self._tracker,
            label        = label,
            trigger      = "manual",
            notes        = notes,
        )

    def diff_snapshots(self, snap_id_a: str, snap_id_b: str) -> Dict:
        return self.snapshots.diff(snap_id_a, snap_id_b)

    # ------------------------------------------------------------------
    # Combined record — one call for the evolution engine
    # ------------------------------------------------------------------

    def record_evolved_alpha(
        self,
        strategy_id:     str,
        parent_id:       Optional[str]  = None,
        family:          str            = "unknown",
        regime:          str            = "all",
        sharpe:          float          = 0.0,
        drawdown:        float          = 0.0,
        profit_factor:   float          = 0.0,
        win_rate:        float          = 0.0,
        trade_count:     int            = 0,
        mutation_ops:    Optional[List[str]] = None,
        parameter_delta: Optional[Dict]     = None,
        run_id:          Optional[str]  = None,
        tags:            Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        All-in-one call for the evolution engine.

        Records an evolved alpha in:
          1. AlphaMemoryStore (statistical identity)
          2. StrategyGenealogy (parent-child tree)
          3. PerformanceArchive (backtest slice)
          4. ExperimentTracker (if run_id provided)

        Returns dict of created object ids.
        """
        # 1. Alpha record
        alpha = self.alpha_store.record_from_dict({
            "strategy_id":   strategy_id,
            "parent_id":     parent_id,
            "family":        family,
            "regime":        regime,
            "sharpe":        sharpe,
            "drawdown":      drawdown,
            "profit_factor": profit_factor,
            "win_rate":      win_rate,
            "trade_count":   trade_count,
            "status":        "discovered",
            "tags":          tags or [],
        })

        # 2. Genealogy
        if parent_id:
            self.genealogy.register_mutation(
                child_id        = strategy_id,
                parent_id       = parent_id,
                family          = family,
                mutation_ops    = mutation_ops or [],
                parameter_delta = parameter_delta or {},
                birth_sharpe    = sharpe,
                birth_drawdown  = drawdown,
                birth_regime    = regime,
            )
        else:
            self.register_seed(
                strategy_id  = strategy_id,
                family       = family,
                birth_sharpe = sharpe,
                birth_regime = regime,
            )

        # 3. Performance
        self.performance.add_slice_from_dict({
            "strategy_id":   strategy_id,
            "phase":         "backtest",
            "regime":        regime,
            "sharpe":        sharpe,
            "drawdown":      drawdown,
            "profit_factor": profit_factor,
            "win_rate":      win_rate,
            "trade_count":   trade_count,
        })

        # 4. Experiment (optional)
        exp_id = None
        if run_id:
            rid = run_id
            exp = self.tracker.create_experiment(
                run_id         = rid,
                strategy_id    = strategy_id,
                exp_type       = "EVOLUTION",
                parameters     = parameter_delta or {},
                regime_context = regime,
            )
            self.tracker.start(exp.exp_id)
            self.tracker.complete(
                exp.exp_id,
                metrics  = {"sharpe": sharpe, "drawdown": drawdown,
                            "profit_factor": profit_factor, "win_rate": win_rate},
                alpha_id = strategy_id,
            )
            exp_id = exp.exp_id

        return {
            "strategy_id": strategy_id,
            "alpha_id":    alpha.strategy_id,
            "exp_id":      exp_id,
        }

    # ------------------------------------------------------------------
    # System summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a combined summary across all sub-systems."""
        result: Dict[str, Any] = {}
        try:
            result["alphas"] = self.alpha_store.stats_summary()
        except Exception:
            result["alphas"] = {}
        try:
            result["genealogy"] = self.genealogy.summary()
        except Exception:
            result["genealogy"] = {}
        try:
            result["performance"] = self.performance.system_summary()
        except Exception:
            result["performance"] = {}
        try:
            latest = self.snapshots.latest()
            result["latest_snapshot"] = latest.to_dict() if latest else None
        except Exception:
            result["latest_snapshot"] = None
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_default_run(self) -> str:
        if self._default_run_id is None:
            import time
            self._default_run_id = self.tracker.open_run(
                name        = f"default_run_{time.strftime('%Y_%m_%d')}",
                objective   = "Ad-hoc experiments",
            )
        return self._default_run_id
