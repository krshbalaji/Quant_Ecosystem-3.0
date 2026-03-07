"""
quant_ecosystem/alpha_genome/_memory_bridge.py
================================================
Genome → ResearchMemoryLayer Bridge — Quant Ecosystem 3.0

Single, thin adapter used by all five genome modules.

Design principles
-----------------
• If research_memory is None  →  every call is a silent no-op (zero cost).
• All public methods catch *all* exceptions internally — genome evolution
  must never be blocked by a memory write failure.
• Lazy family detection — infers the strategy family from genome signal_gene
  when not explicitly provided.
• Thread-safe: no shared mutable state; ResearchMemoryLayer is already
  internally thread-safe.

Canonical call-sites
--------------------
  GenomeGenerator  → bridge.record_seed()
  GenomeMutator    → bridge.record_mutation()
  GenomeCrossbreeder → bridge.record_crossover()
  GenomeEvaluator  → bridge.record_evaluation()
  GenomeSnapshot   → bridge.snapshot()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _infer_family(genome: Dict) -> str:
    """Derive a strategy family string from the genome's signal gene."""
    try:
        signal = genome.get("signal_gene") or {}
        sig_type  = str(signal.get("type", "")).lower().replace(" ", "_")
        indicator = str(signal.get("indicator_1", "")).upper()
        tf        = str(signal.get("timeframe", "")).lower()
        if sig_type:
            return f"{sig_type}_{indicator}_{tf}".strip("_")
    except Exception:
        pass
    return "unknown"


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


class GenomeMemoryBridge:
    """
    Non-blocking adapter between the alpha-genome pipeline and
    ResearchMemoryLayer.

    Usage
    -----
        bridge = GenomeMemoryBridge(research_memory=router.research_memory)

        # On new random genome
        bridge.record_seed(genome)

        # On mutation
        bridge.record_mutation(parent_genome, child_genome, ops=["tweak_threshold"])

        # On crossover
        bridge.record_crossover(parent_a, parent_b, child)

        # On evaluation
        bridge.record_evaluation(genome_id, metrics={...}, genome=genome)

        # Nightly snapshot
        bridge.snapshot(label="eod_genome_cycle", quant_mode="PAPER")
    """

    def __init__(
        self,
        research_memory=None,
        default_run_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        self._rm            = research_memory
        self._run_id        = default_run_id
        self._active        = research_memory is not None

    # ------------------------------------------------------------------
    # Setter — allows late injection (e.g. after SystemFactory boot)
    # ------------------------------------------------------------------

    def set_research_memory(self, research_memory) -> None:
        self._rm     = research_memory
        self._active = research_memory is not None

    def is_active(self) -> bool:
        return self._active

    # ------------------------------------------------------------------
    # Core hooks
    # ------------------------------------------------------------------

    def record_seed(self, genome: Dict, regime: str = "all") -> None:
        """Record a freshly generated (seed) genome."""
        if not self._active:
            return
        try:
            gid    = str(genome.get("genome_id", ""))
            family = _infer_family(genome)
            self._rm.record_evolved_alpha(
                strategy_id  = gid,
                parent_id    = None,
                family       = family,
                regime       = regime,
                sharpe       = 0.0,
                drawdown     = 0.0,
                trade_count  = 0,
                mutation_ops = ["seed_generation"],
                run_id       = self._ensure_run(),
                tags         = ["genome", "seed", family],
            )
            logger.debug("[MemoryBridge] seed recorded: %s", gid)
        except Exception as exc:
            logger.debug("[MemoryBridge] record_seed failed silently: %s", exc)

    def record_mutation(
        self,
        parent:      Dict,
        child:       Dict,
        ops:         Optional[List[str]] = None,
        regime:      str                 = "all",
        generation:  int                 = 0,
    ) -> None:
        """Record parent → child mutation genealogy."""
        if not self._active:
            return
        try:
            parent_id = str(parent.get("genome_id", "unknown"))
            child_id  = str(child.get("genome_id",  "unknown"))
            family    = _infer_family(child)
            delta     = self._parameter_delta(parent, child)
            gen       = _safe_int(
                child.get("metadata", {}).get("generation", generation)
            )
            self._rm.register_mutation(
                child_id        = child_id,
                parent_id       = parent_id,
                family          = family,
                mutation_ops    = ops or ["mutate"],
                parameter_delta = delta,
                birth_sharpe    = 0.0,
                birth_regime    = regime,
            )
            logger.debug("[MemoryBridge] mutation recorded: %s → %s (gen %d)",
                         parent_id, child_id, gen)
        except Exception as exc:
            logger.debug("[MemoryBridge] record_mutation failed silently: %s", exc)

    def record_crossover(
        self,
        parent_a: Dict,
        parent_b: Dict,
        child:    Dict,
        regime:   str = "all",
    ) -> None:
        """Record two-parent crossover genealogy."""
        if not self._active:
            return
        try:
            aid    = str(parent_a.get("genome_id", "A"))
            bid    = str(parent_b.get("genome_id", "B"))
            cid    = str(child.get("genome_id",    "child"))
            family = _infer_family(child)
            self._rm.genealogy.register_crossover(
                child_id       = cid,
                parent_a_id    = aid,
                parent_b_id    = bid,
                family         = family,
                birth_sharpe   = 0.0,
                birth_regime   = regime,
            )
            # Also register in alpha store as a discovered alpha
            self._rm.alpha_store.record_from_dict({
                "strategy_id": cid,
                "parent_id":   aid,
                "family":      family,
                "regime":      regime,
                "sharpe":      0.0,
                "drawdown":    0.0,
                "trade_count": 0,
                "mutation_type": "crossover",
                "status":      "discovered",
                "tags":        ["genome", "crossover", family],
            })
            logger.debug("[MemoryBridge] crossover recorded: %s × %s → %s",
                         aid, bid, cid)
        except Exception as exc:
            logger.debug("[MemoryBridge] record_crossover failed silently: %s", exc)

    def record_evaluation(
        self,
        genome_id:     str,
        metrics:       Dict[str, float],
        genome:        Optional[Dict]  = None,
        regime:        str             = "all",
        phase:         str             = "backtest",
    ) -> None:
        """
        Archive evaluation metrics into PerformanceArchive and update
        AlphaMemoryStore with live alpha statistics.
        """
        if not self._active:
            return
        try:
            sharpe    = _safe_float(metrics.get("sharpe"))
            drawdown  = -abs(_safe_float(metrics.get("drawdown")))   # ensure negative
            pf        = _safe_float(metrics.get("profit_factor"), 1.0)
            win_rate  = _safe_float(metrics.get("win_rate"))
            tc        = _safe_int(metrics.get("trade_count"))
            fitness   = _safe_float(metrics.get("fitness_score"))
            family    = _infer_family(genome) if genome else "unknown"

            # 1. Archive performance slice
            self._rm.performance.add_slice_from_dict({
                "strategy_id":   genome_id,
                "phase":         phase,
                "regime":        regime,
                "sharpe":        sharpe,
                "drawdown":      drawdown,
                "profit_factor": pf,
                "win_rate":      win_rate,
                "trade_count":   tc,
            })

            # 2. Update or create alpha record with latest stats
            existing = self._rm.alpha_store.get(genome_id)
            if existing is not None:
                # Patch live stats if this is a live evaluation
                if phase in ("live", "shadow"):
                    self._rm.alpha_store.update_live_stats(
                        genome_id,
                        live_sharpe      = sharpe,
                        live_drawdown    = drawdown,
                        live_trade_count = tc,
                    )
                else:
                    # Update backtest stats
                    existing.sharpe        = sharpe
                    existing.drawdown      = drawdown
                    existing.profit_factor = pf
                    existing.win_rate      = win_rate
                    existing.trade_count   = tc
                    existing.extra["fitness_score"] = fitness
                    self._rm.alpha_store.record(existing)
            else:
                self._rm.alpha_store.record_from_dict({
                    "strategy_id":   genome_id,
                    "family":        family,
                    "regime":        regime,
                    "sharpe":        sharpe,
                    "drawdown":      drawdown,
                    "profit_factor": pf,
                    "win_rate":      win_rate,
                    "trade_count":   tc,
                    "status":        "discovered",
                    "extra":         {"fitness_score": fitness},
                    "tags":          ["genome", "evaluated", family],
                })

            logger.debug("[MemoryBridge] evaluation recorded: %s sharpe=%.4f fitness=%.4f",
                         genome_id, sharpe, fitness)
        except Exception as exc:
            logger.debug("[MemoryBridge] record_evaluation failed silently: %s", exc)

    def record_library_store(
        self,
        genome_id: str,
        genome:    Dict,
        generation: int = 0,
        fitness_score: float = 0.0,
    ) -> None:
        """Called when a genome is stored in GenomeLibrary."""
        if not self._active:
            return
        try:
            existing = self._rm.alpha_store.get(genome_id)
            if existing is None:
                family = _infer_family(genome)
                self._rm.alpha_store.record_from_dict({
                    "strategy_id": genome_id,
                    "family":      family,
                    "regime":      "all",
                    "status":      "discovered",
                    "trade_count": 0,
                    "extra": {
                        "fitness_score": fitness_score,
                        "generation":    generation,
                    },
                    "tags": ["genome", "library"],
                })
        except Exception as exc:
            logger.debug("[MemoryBridge] record_library_store failed silently: %s", exc)

    def snapshot(
        self,
        label:      str = "",
        notes:      str = "",
        quant_mode: str = "PAPER",
        trigger:    str = "scheduled",
    ) -> Optional[Any]:
        """Take a full research snapshot."""
        if not self._active:
            return None
        try:
            snap = self._rm.snapshots.create(
                alpha_store  = self._rm._alpha_store,
                genealogy    = self._rm._genealogy,
                perf_archive = self._rm._perf,
                tracker      = self._rm._tracker,
                label        = label or "genome_cycle_snapshot",
                trigger      = trigger,
                notes        = notes,
                quant_mode   = quant_mode,
            )
            logger.info("[MemoryBridge] snapshot created: %s (%d alphas)",
                        snap.manifest.snapshot_id, snap.manifest.alpha_count)
            return snap
        except Exception as exc:
            logger.warning("[MemoryBridge] snapshot failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_run(self) -> Optional[str]:
        """Return or lazily create a default experiment run."""
        if self._rm is None:
            return None
        try:
            if self._run_id is None:
                import time
                self._run_id = self._rm.tracker.open_run(
                    name      = f"genome_evolution_{time.strftime('%Y_%m_%d')}",
                    objective = "Autonomous genome evolution cycle",
                )
            return self._run_id
        except Exception:
            return None

    @staticmethod
    def _parameter_delta(parent: Dict, child: Dict) -> Dict[str, Any]:
        """
        Compute a shallow diff of the six gene dicts between parent and child.
        Only scalar-changed fields are included.
        """
        gene_keys = (
            "market_filter_gene", "signal_gene", "entry_gene",
            "exit_gene", "risk_gene", "execution_gene",
        )
        delta: Dict[str, Any] = {}
        for key in gene_keys:
            pg = parent.get(key) or {}
            cg = child.get(key)  or {}
            for field, cval in cg.items():
                pval = pg.get(field)
                if pval != cval and not isinstance(cval, dict):
                    delta[f"{key}.{field}"] = {"before": pval, "after": cval}
        return delta
