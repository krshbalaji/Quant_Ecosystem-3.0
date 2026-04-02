"""
quant_ecosystem/meta_research/meta_research_ai.py
==================================================
Meta-Research AI layer — Quant Ecosystem 3.0

Analyses the GenomeLibrary, ResearchGrid result store, PerformanceStore and
RegimeEngine each cycle and emits a ResearchPriorities object that guides the
next StrategyDiscoveryEngine batch.

Architecture
------------

    GenomeLibrary        — library size, family fitness, top/weak families
    ResearchGrid         — recent job results, fitness trend, best family
    PerformanceStore     — live trade win-rates by strategy / family
    RegimeEngine         — current market regime string

    MetaResearchAI._synthesise()
        → ResearchPriorities(focus_family, mutation_rate, explore_markets,
                              batch_size, indicators, timeframe_mix,
                              regime_bias, confidence, reasoning, ...)

Construction
------------
All four data sources are optional and can be injected at any time via
set_genome_library() / set_research_grid() / set_performance_store() /
set_regime_engine().  The system continues with safe defaults if any or
all sources are absent.

SystemFactory calls
-------------------
    MetaResearchAI(
        genome_library          = router.genome_library,
        research_grid           = router.research_grid,
        performance_store       = perf_store,
        regime_engine           = router.regime_ai_engine or router.market_regime_detector,
        refresh_interval_sec    = 60.0,
        min_samples_for_confidence = 10,
    )
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Family → default indicator list ──────────────────────────────────────────
_FAMILY_INDICATORS: Dict[str, List[str]] = {
    "trend":          ["momentum", "ma_cross"],
    "mean_reversion": ["mean_reversion", "rsi"],
    "breakout":       ["breakout", "volatility_breakout"],
    "volatility":     ["volatility_breakout"],
    "stat_arb":       ["mean_reversion", "rsi"],
    "momentum":       ["momentum", "ma_cross"],
    "oscillator":     ["rsi"],
}

# ── Regime → preferred family ─────────────────────────────────────────────────
_REGIME_FAMILY_AFFINITY: Dict[str, str] = {
    "TRENDING":      "trend",
    "RANGE_BOUND":   "mean_reversion",
    "VOLATILE":      "breakout",
    "BREAKOUT":      "breakout",
    "BULL":          "momentum",
    "BEAR":          "mean_reversion",
}

_ALL_FAMILIES = list(_FAMILY_INDICATORS.keys())


# ─────────────────────────────────────────────────────────────────────────────
# ResearchPriorities dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResearchPriorities:
    """
    Recommended research parameters emitted by MetaResearchAI each cycle.

    Fields
    ------
    focus_family    Family most likely to yield high-fitness genomes.
    explore_markets Asset-class tokens to evaluate against (e.g. ["NSE","CRYPTO"]).
    mutation_rate   Fraction of next batch that should be mutations (0.05–0.50).
    regime_bias     Current regime string used in reasoning.
    timeframe_mix   Recommended timeframes for the next batch.
    batch_size      Recommended genome batch size.
    indicators      Ordered indicator list for sampling.
    confidence      0.0 (no data) → 1.0 (fully data-driven).
    reasoning       Human-readable audit trail of the synthesis decisions.
    generated_at    Unix timestamp of this object.
    memory_snapshot Raw analysis snapshots used to produce this object.
    """
    focus_family:    str             = "momentum"
    explore_markets: List[str]       = field(default_factory=lambda: ["NSE", "CRYPTO"])
    mutation_rate:   float           = 0.15
    regime_bias:     str             = "UNKNOWN"
    timeframe_mix:   List[str]       = field(default_factory=lambda: ["5m", "1h"])
    batch_size:      int             = 20
    indicators:      List[str]       = field(default_factory=lambda: ["momentum", "ma_cross"])
    confidence:      float           = 0.0
    reasoning:       str             = ""
    generated_at:    float           = field(default_factory=time.time)
    memory_snapshot: Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "focus_family":    self.focus_family,
            "explore_markets": list(self.explore_markets),
            "mutation_rate":   round(self.mutation_rate, 4),
            "regime_bias":     self.regime_bias,
            "timeframe_mix":   list(self.timeframe_mix),
            "batch_size":      self.batch_size,
            "indicators":      list(self.indicators),
            "confidence":      round(self.confidence, 4),
            "reasoning":       self.reasoning,
            "generated_at":    self.generated_at,
            "memory_snapshot": self.memory_snapshot,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MetaResearchAI
# ─────────────────────────────────────────────────────────────────────────────

class MetaResearchAI:
    """
    Self-optimising research controller.

    Analyses historical performance data from all available sources and
    emits ResearchPriorities objects that StrategyDiscoveryEngine uses to
    bias its genome generation batch.

    Parameters
    ----------
    genome_library:
        GenomeLibrary instance (read-only analysis; library is never modified).
    research_grid:
        ResearchGrid / ParallelResearchGrid instance for result analysis.
    performance_store:
        PerformanceStore tracking live trade outcomes by strategy.
    regime_engine:
        RegimeDetector or RegimeAICore providing current regime string.
    refresh_interval_sec:
        Minimum seconds between full re-analyses.  Calls within the TTL
        return the cached ResearchPriorities without re-analysis.
    min_samples_for_confidence:
        Minimum number of evaluated genomes required before confidence > 0.
    """

    def __init__(
        self,
        genome_library=None,
        research_grid=None,
        performance_store=None,
        regime_engine=None,
        refresh_interval_sec: float = 60.0,
        min_samples_for_confidence: int = 10,
        # Legacy compat: accept router keyword arg silently
        router=None,
    ) -> None:
        self._genome_library    = genome_library
        self._research_grid     = research_grid
        self._performance_store = performance_store
        self._regime_engine     = regime_engine

        self._refresh_interval  = max(0.0, float(refresh_interval_sec))
        self._min_samples       = max(1, int(min_samples_for_confidence))

        self._lock              = threading.Lock()
        self._cached:  Optional[ResearchPriorities] = None
        self._last_ts: float   = 0.0

        # Diagnostics
        self._total_calls:   int = 0
        self._refresh_count: int = 0

        # Legacy: if router provided (old interface), try to extract sources
        if router is not None:
            self._genome_library    = self._genome_library    or getattr(router, "genome_library",    None)
            self._research_grid     = self._research_grid     or getattr(router, "research_grid",     None)
            self._regime_engine     = self._regime_engine     or getattr(router, "regime_ai_engine",  None)

        logger.info(
            "MetaResearchAI initialized | interval=%.0fs min_samples=%d "
            "lib=%s grid=%s perf=%s regime=%s",
            self._refresh_interval, self._min_samples,
            "yes" if self._genome_library    is not None else "no",
            "yes" if self._research_grid     is not None else "no",
            "yes" if self._performance_store is not None else "no",
            "yes" if self._regime_engine     is not None else "no",
        )

    # ── Late injection ─────────────────────────────────────────────────────────

    def set_genome_library(self, lib: Any) -> None:
        self._genome_library = lib
        logger.debug("MetaResearchAI: GenomeLibrary injected.")

    def set_research_grid(self, grid: Any) -> None:
        self._research_grid = grid
        logger.debug("MetaResearchAI: ResearchGrid injected.")

    def set_performance_store(self, store: Any) -> None:
        self._performance_store = store
        logger.debug("MetaResearchAI: PerformanceStore injected.")

    def set_regime_engine(self, engine: Any) -> None:
        self._regime_engine = engine
        logger.debug("MetaResearchAI: RegimeEngine injected.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def prioritise(self, *, force: bool = False) -> ResearchPriorities:
        """
        Return current ResearchPriorities, re-analysing if the TTL has expired.

        Parameters
        ----------
        force : bool
            If True, skip the TTL check and force an immediate re-analysis.

        Returns
        -------
        ResearchPriorities — always a valid object even if all sources fail.
        """
        self._total_calls += 1
        now = time.time()

        with self._lock:
            cache_valid = (
                self._cached is not None
                and not force
                and (now - self._last_ts) < self._refresh_interval
            )
            if cache_valid:
                return self._cached

        try:
            priorities = self._analyse_and_synthesise()
        except Exception as exc:
            logger.warning("MetaResearchAI.prioritise: analysis failed (%s) — using defaults.", exc)
            priorities = self._defaults()

        with self._lock:
            self._cached  = priorities
            self._last_ts = time.time()
            self._refresh_count += 1

        return priorities

    def get_priorities(self) -> Dict[str, Any]:
        """Return current priorities as a plain dict (calls prioritise() internally)."""
        return self.prioritise().to_dict()

    def force_refresh(self) -> ResearchPriorities:
        """Force an immediate re-analysis and return the new ResearchPriorities."""
        return self.prioritise(force=True)

    def status(self) -> Dict[str, Any]:
        """Return diagnostic snapshot."""
        with self._lock:
            cached = self._cached
            last_ts = self._last_ts
        return {
            "total_prioritise_calls": self._total_calls,
            "refresh_count":          self._refresh_count,
            "last_refresh_ts":        last_ts,
            "cache_age_sec":          round(max(0.0, time.time() - last_ts), 2),
            "refresh_interval_sec":   self._refresh_interval,
            "last_focus_family":      cached.focus_family if cached else None,
            "last_confidence":        round(cached.confidence, 4) if cached else None,
            "last_mutation_rate":     round(cached.mutation_rate, 4) if cached else None,
            "sources": {
                "genome_library":    self._genome_library    is not None,
                "research_grid":     self._research_grid     is not None,
                "performance_store": self._performance_store is not None,
                "regime_engine":     self._regime_engine     is not None,
            },
        }

    # ── Analysis pipeline ──────────────────────────────────────────────────────

    def _analyse_and_synthesise(self) -> ResearchPriorities:
        genome_snap  = self._analyse_genome_library()
        grid_snap    = self._analyse_grid_results()
        perf_snap    = self._analyse_performance()
        regime       = self._analyse_regime()
        return self._synthesise(genome_snap, grid_snap, perf_snap, regime)

    def _analyse_genome_library(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {
            "total_genomes": 0, "family_counts": {}, "family_fitness": {},
            "family_market": {}, "top_families": [], "weak_families": [], "available": False,
        }
        lib = self._genome_library
        if lib is None:
            return snap
        try:
            ids = lib.list_genomes() if hasattr(lib, "list_genomes") else list(getattr(lib, "genomes", {}).keys())
            snap["total_genomes"] = len(ids)
            snap["available"] = bool(ids)

            family_fitness:   Dict[str, List[float]] = {}
            family_markets:   Dict[str, List[str]]   = {}
            family_counts:    Dict[str, int]          = {}

            for gid in ids:
                try:
                    g = lib.get_genome(gid) if hasattr(lib, "get_genome") else lib.get(gid)
                    if g is None:
                        continue
                    fam   = _infer_family(g, gid)
                    score = float(g.get("fitness_score", 0.0))
                    asset = str((g.get("market_filter_gene") or {}).get("asset_class", "stocks")).lower()
                    family_counts[fam]  = family_counts.get(fam, 0) + 1
                    family_fitness.setdefault(fam, []).append(score)
                    family_markets.setdefault(fam, []).append(asset)
                except Exception:
                    continue

            snap["family_counts"] = family_counts
            snap["family_fitness"] = {
                f: round(sum(v) / len(v), 4) for f, v in family_fitness.items() if v
            }
            snap["family_market"] = {
                f: _mode(v) for f, v in family_markets.items() if v
            }
            sorted_fams = sorted(snap["family_fitness"].items(), key=lambda x: x[1], reverse=True)
            snap["top_families"]  = [f for f, _ in sorted_fams[:3] if _ > 0]
            snap["weak_families"] = [f for f, _ in sorted_fams if _ <= 0]
        except Exception as exc:
            logger.debug("MetaResearchAI._analyse_genome_library failed: %s", exc)
        return snap

    def _analyse_grid_results(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {
            "total_results": 0, "recent_count": 0, "avg_fitness": 0.0,
            "fitness_trend": 0.0, "job_type_breakdown": {}, "best_family": None,
            "worst_family": None, "available": False,
        }
        grid = self._research_grid
        if grid is None:
            return snap
        try:
            # Try result_store, then top_results
            results = []
            rs = getattr(grid, "_result_store", None) or getattr(grid, "result_store", None)
            if rs is not None and hasattr(rs, "_results"):
                all_r = list(rs._results.values())
                results = [r for r in all_r if getattr(r, "ok", False)][-200:]
            elif hasattr(grid, "top_results"):
                results = grid.top_results(200) or []
            elif hasattr(grid, "_results"):
                results = list(grid._results.values())[-200:]

            if not results:
                return snap

            snap["total_results"] = len(results)
            snap["available"]     = True

            fitness_vals: List[float] = []
            family_fitness: Dict[str, List[float]] = {}

            for r in results:
                fit = float(getattr(r, "fitness", None) or (r.get("fitness", 0) if isinstance(r, dict) else 0))
                fid = str(getattr(r, "genome_id", "") or (r.get("genome_id", "") if isinstance(r, dict) else ""))
                fam = _infer_family_from_id(fid)
                fitness_vals.append(fit)
                family_fitness.setdefault(fam, []).append(fit)

            if fitness_vals:
                snap["avg_fitness"]   = round(sum(fitness_vals) / len(fitness_vals), 4)
                recent = fitness_vals[-min(20, len(fitness_vals)):]
                old    = fitness_vals[: max(1, len(fitness_vals) - len(recent))]
                snap["fitness_trend"] = round(
                    (sum(recent) / len(recent)) - (sum(old) / len(old)), 4
                )

            sorted_fam = sorted(
                {f: sum(v) / len(v) for f, v in family_fitness.items()}.items(),
                key=lambda x: x[1], reverse=True,
            )
            snap["best_family"]  = sorted_fam[0][0] if sorted_fam else None
            snap["worst_family"] = sorted_fam[-1][0] if sorted_fam else None
            snap["recent_count"] = len(results)
        except Exception as exc:
            logger.debug("MetaResearchAI._analyse_grid_results failed: %s", exc)
        return snap

    def _analyse_performance(self) -> Dict[str, Any]:
        snap: Dict[str, Any] = {
            "total_strategies": 0, "best_strategy": None, "worst_strategy": None,
            "family_win_rates": {}, "avg_sharpe": 0.0, "avg_win_rate": 0.0, "available": False,
        }
        ps = self._performance_store
        if ps is None:
            return snap
        try:
            all_m = (
                ps.get_all_metrics() if hasattr(ps, "get_all_metrics")
                else getattr(ps, "_metrics", {})
            )
            if not all_m:
                return snap

            snap["total_strategies"] = len(all_m)
            snap["available"]        = True

            sharpes:    List[float] = []
            win_rates:  List[float] = []
            fam_wr:     Dict[str, List[float]] = {}

            best_sid, best_wr   = None, -1.0
            worst_sid, worst_wr = None, 101.0

            for sid, m in all_m.items():
                wr = float(m.get("win_rate", 0.0) or 0.0)
                sh = float(m.get("sharpe",   0.0) or 0.0)
                fam = _infer_family_from_id(str(sid))
                sharpes.append(sh)
                win_rates.append(wr)
                fam_wr.setdefault(fam, []).append(wr)
                if wr > best_wr:
                    best_wr, best_sid = wr, sid
                if wr < worst_wr:
                    worst_wr, worst_sid = wr, sid

            snap["best_strategy"]  = best_sid
            snap["worst_strategy"] = worst_sid
            snap["avg_sharpe"]     = round(sum(sharpes) / len(sharpes), 4) if sharpes else 0.0
            snap["avg_win_rate"]   = round(sum(win_rates) / len(win_rates), 4) if win_rates else 0.0
            snap["family_win_rates"] = {
                f: round(sum(v) / len(v), 4) for f, v in fam_wr.items() if v
            }
        except Exception as exc:
            logger.debug("MetaResearchAI._analyse_performance failed: %s", exc)
        return snap

    def _analyse_regime(self) -> str:
        engine = self._regime_engine
        if engine is None:
            return "UNKNOWN"
        try:
            for attr in ("current_regime", "regime", "last_regime"):
                val = getattr(engine, attr, None)
                if val is not None:
                    return str(val).upper()
            if hasattr(engine, "classify"):
                return str(engine.classify()).upper()
            if hasattr(engine, "detect"):
                return str(engine.detect()).upper()
        except Exception as exc:
            logger.debug("MetaResearchAI._analyse_regime failed: %s", exc)
        return "UNKNOWN"

    # ── Synthesis ──────────────────────────────────────────────────────────────

    def _synthesise(
        self,
        genome_snap: Dict,
        grid_snap:   Dict,
        perf_snap:   Dict,
        regime:      str,
    ) -> ResearchPriorities:
        notes: List[str] = [f"regime={regime}"]

        # ── focus_family ──────────────────────────────────────────────────────
        focus_family = "momentum"  # ultimate fallback

        # 1. Live win-rate leader
        fam_wr = perf_snap.get("family_win_rates", {})
        if fam_wr:
            live_leader = max(fam_wr, key=fam_wr.get)
            if fam_wr[live_leader] > 50.0:
                focus_family = live_leader
                notes.append(f"focus={focus_family}(live_wr={fam_wr[live_leader]:.1f})")

        # 2. Genome library leader (top fitness family)
        elif genome_snap.get("top_families"):
            lib_leader = genome_snap["top_families"][0]
            focus_family = lib_leader
            notes.append(f"focus={focus_family}(lib_leader={lib_leader})")

        # 3. Regime affinity
        else:
            affinity = _REGIME_FAMILY_AFFINITY.get(regime, "")
            if affinity:
                focus_family = affinity
            notes.append(f"focus={focus_family}(regime={regime})")

        # ── mutation_rate ─────────────────────────────────────────────────────
        total_genomes = genome_snap.get("total_genomes", 0)
        fitness_trend = grid_snap.get("fitness_trend", 0.0)

        mutation_rate = 0.10  # base
        reason_parts: List[str] = []

        if total_genomes < self._min_samples:
            mutation_rate += 0.05
            reason_parts.append("early_stage(+0.05)")
        elif total_genomes > 200:
            mutation_rate += 0.10
            reason_parts.append("large_lib(+0.10)")

        if fitness_trend < -0.05:
            mutation_rate += 0.10
            reason_parts.append("declining_fitness(+0.10)")
        elif fitness_trend > 0.05:
            mutation_rate -= 0.05
            reason_parts.append("improving_fitness(-0.05)")

        weak = genome_snap.get("weak_families", [])
        if focus_family in weak:
            mutation_rate += 0.05
            reason_parts.append("focus_weak(+0.05)")

        mutation_rate = round(max(0.05, min(0.50, mutation_rate)), 4)
        notes.append(f"mutation={mutation_rate}({'|'.join(reason_parts) or 'base'})")

        # ── explore_markets ───────────────────────────────────────────────────
        explore_markets: List[str] = []
        fam_market = genome_snap.get("family_market", {})
        if fam_market.get(focus_family):
            raw = str(fam_market[focus_family]).upper()
            mkt_map = {
                "STOCKS":      "NSE",
                "INDICES":     "NSE",
                "CRYPTO":      "CRYPTO",
                "FOREX":       "FOREX",
                "COMMODITIES": "MCX",
            }
            tok = mkt_map.get(raw, raw)
            if tok:
                explore_markets = [tok, "CRYPTO"] if tok != "CRYPTO" else ["CRYPTO", "NSE"]
        if not explore_markets:
            explore_markets = ["NSE", "CRYPTO"]

        # ── batch_size ────────────────────────────────────────────────────────
        if total_genomes < 20:
            batch_size = 20
        elif total_genomes < 100:
            batch_size = 30
        else:
            batch_size = 40

        # ── indicators ───────────────────────────────────────────────────────
        indicators = list(_FAMILY_INDICATORS.get(focus_family, ["momentum", "ma_cross"]))
        # Add indicators from secondary families
        top_fams = genome_snap.get("top_families", [])
        for fam in top_fams:
            for ind in _FAMILY_INDICATORS.get(fam, []):
                if ind not in indicators:
                    indicators.append(ind)

        # ── timeframe_mix ─────────────────────────────────────────────────────
        if regime in ("TRENDING", "BREAKOUT", "BULL"):
            timeframe_mix = ["1h", "4h", "1d"]
        elif regime in ("RANGE_BOUND", "MEAN_REVERSION"):
            timeframe_mix = ["5m", "15m", "1h"]
        elif regime in ("VOLATILE",):
            timeframe_mix = ["5m", "15m"]
        else:
            timeframe_mix = ["5m", "1h"]

        # ── confidence ────────────────────────────────────────────────────────
        total_samples = (
            total_genomes
            + grid_snap.get("total_results", 0)
            + perf_snap.get("total_strategies", 0)
        )
        if total_samples <= 0:
            confidence = 0.0
        else:
            confidence = min(1.0, total_samples / max(1, self._min_samples * 10))
            confidence = round(confidence, 4)
        notes.append(f"samples={total_samples} | confidence={confidence:.2f}")

        reasoning = " | ".join(notes)

        return ResearchPriorities(
            focus_family    = focus_family,
            explore_markets = explore_markets,
            mutation_rate   = mutation_rate,
            regime_bias     = regime,
            timeframe_mix   = timeframe_mix,
            batch_size      = batch_size,
            indicators      = indicators,
            confidence      = confidence,
            reasoning       = reasoning,
            generated_at    = time.time(),
            memory_snapshot = {
                "genome_library": genome_snap,
                "grid_results":   grid_snap,
                "performance":    perf_snap,
                "regime":         regime,
            },
        )

    # ── Safe defaults ──────────────────────────────────────────────────────────

    @staticmethod
    def _defaults() -> ResearchPriorities:
        return ResearchPriorities(
            focus_family    = "momentum",
            explore_markets = ["NSE", "CRYPTO"],
            mutation_rate   = 0.15,
            regime_bias     = "UNKNOWN",
            timeframe_mix   = ["5m", "1h"],
            batch_size      = 20,
            indicators      = ["momentum", "ma_cross"],
            confidence      = 0.0,
            reasoning       = "safe_defaults",
            generated_at    = time.time(),
            memory_snapshot = {},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module helpers
# ─────────────────────────────────────────────────────────────────────────────

def _infer_family(genome: Dict[str, Any], genome_id: str = "") -> str:
    sg  = genome.get("signal_gene") or {}
    ind = str(sg.get("indicator", "")).lower()
    fam_map = {
        "momentum":           "momentum",
        "ma_cross":           "trend",
        "ema_cross":          "trend",
        "mean_reversion":     "mean_reversion",
        "rsi":                "oscillator",
        "breakout":           "breakout",
        "volatility_breakout":"volatility",
    }
    if ind in fam_map:
        return fam_map[ind]
    fam = str(genome.get("family", "")).lower()
    if fam in _FAMILY_INDICATORS:
        return fam
    return _infer_family_from_id(genome_id)


def _infer_family_from_id(genome_id: str) -> str:
    gid = genome_id.lower()
    for fam in _ALL_FAMILIES:
        if fam in gid:
            return fam
    return "momentum"


def _mode(values: List[str]) -> str:
    if not values:
        return ""
    counts: Dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get)
