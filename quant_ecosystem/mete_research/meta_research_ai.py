"""
meta_research_ai.py — Quant Ecosystem 3.0
==========================================

Meta-Research AI layer that sits above StrategyDiscoveryEngine and guides
what the parallel research grid should search for next.

Architecture
------------

  ┌────────────────────────────────────────────────────────────┐
  │                     MetaResearchAI                         │
  │                                                            │
  │  Inputs (ResearchMemory)       Output (ResearchPriorities) │
  │  ┌──────────────────────┐      ┌────────────────────────┐  │
  │  │  GenomeLibrary       │─────►│  focus_family          │  │
  │  │  (stored genomes,    │      │  explore_markets       │  │
  │  │   fitness history)   │      │  mutation_rate         │  │
  │  ├──────────────────────┤      │  regime_bias           │  │
  │  │  ResearchGrid        │─────►│  timeframe_mix         │  │
  │  │  ResultStore         │      │  batch_size            │  │
  │  │  (live job results)  │      │  indicators            │  │
  │  ├──────────────────────┤      │  confidence            │  │
  │  │  PerformanceStore    │─────►│  reasoning             │  │
  │  │  (live trade PnL     │      └────────────────────────┘  │
  │  │   by strategy)       │                                   │
  │  └──────────────────────┘                                   │
  └────────────────────────────────────────────────────────────┘

Analysis pipeline (called on every prioritise() invocation)
-----------------------------------------------------------
  1. _analyse_genome_library()   — family counts, avg fitness per family,
                                   top-k genomes, stale families
  2. _analyse_grid_results()     — job-type breakdown, recent fitness
                                   distribution, sharpe trend
  3. _analyse_performance()      — live trade PnL per strategy,
                                   per-family win-rate
  4. _analyse_regime()           — current market regime
  5. _synthesise()               — combine signals → priorities dict

Output schema
-------------
{
    "focus_family":    str,           # signal family to over-sample
    "explore_markets": List[str],     # asset classes / markets to test
    "mutation_rate":   float,         # 0.0–1.0, higher → more exploration
    "regime_bias":     str,           # e.g. "TRENDING", "RANGE_BOUND"
    "timeframe_mix":   List[str],     # e.g. ["5m","1h"]
    "batch_size":      int,           # recommended genome batch size
    "indicators":      List[str],     # ranked indicator list for sampling
    "confidence":      float,         # 0.0–1.0 signal quality
    "reasoning":       str,           # human-readable explanation
    "generated_at":    float,         # epoch timestamp
    "memory_snapshot": Dict           # raw stats that drove the decision
}

Robustness rules
----------------
* All three memory sources are optional.  Missing or broken sources are
  silently skipped; the engine degrades gracefully to safe defaults.
* The ``prioritise()`` method NEVER raises — it always returns a valid
  priorities dict.
* A configurable TTL (``refresh_interval_sec``) throttles re-analysis so
  the engine is inexpensive to call on every discover() cycle.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# All known strategy families mapped to relevant indicators
_FAMILY_INDICATORS: Dict[str, List[str]] = {
    "trend":           ["momentum", "ma_cross", "ema_cross"],
    "mean_reversion":  ["mean_reversion", "rsi", "bollinger"],
    "breakout":        ["breakout", "volatility_breakout"],
    "volatility":      ["volatility_breakout", "atr"],
    "stat_arb":        ["zscore", "mean_reversion", "rsi"],
    "momentum":        ["momentum", "ma_cross"],
    "oscillator":      ["rsi", "stochastic"],
}

_ALL_INDICATORS = sorted({
    ind for inds in _FAMILY_INDICATORS.values() for ind in inds
})

_MARKET_CLASSES = ["NSE", "CRYPTO", "FOREX", "INDICES", "COMMODITIES"]

_REGIME_FAMILY_AFFINITY: Dict[str, str] = {
    "TRENDING":    "trend",
    "RANGE_BOUND": "mean_reversion",
    "VOLATILE":    "breakout",
    "BREAKOUT":    "breakout",
    "UNKNOWN":     "momentum",
}

_DEFAULT_PRIORITIES: Dict[str, Any] = {
    "focus_family":    "momentum",
    "explore_markets": ["NSE", "CRYPTO"],
    "mutation_rate":   0.15,
    "regime_bias":     "UNKNOWN",
    "timeframe_mix":   ["5m", "1h"],
    "batch_size":      20,
    "indicators":      ["momentum", "mean_reversion", "rsi", "breakout"],
    "confidence":      0.0,
    "reasoning":       "defaults — no memory available yet",
    "generated_at":    0.0,
    "memory_snapshot": {},
}


# ─────────────────────────────────────────────────────────────────────────────
# ResearchPriorities dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResearchPriorities:
    """
    Structured output of a single MetaResearchAI analysis cycle.

    All fields have safe defaults so callers can always read them even if
    the analysis produced nothing useful.
    """

    focus_family:    str             = "momentum"
    explore_markets: List[str]       = field(default_factory=lambda: ["NSE", "CRYPTO"])
    mutation_rate:   float           = 0.15
    regime_bias:     str             = "UNKNOWN"
    timeframe_mix:   List[str]       = field(default_factory=lambda: ["5m", "1h"])
    batch_size:      int             = 20
    indicators:      List[str]       = field(default_factory=lambda: ["momentum", "rsi"])
    confidence:      float           = 0.0
    reasoning:       str             = ""
    generated_at:    float           = field(default_factory=time.time)
    memory_snapshot: Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "focus_family":    self.focus_family,
            "explore_markets": self.explore_markets,
            "mutation_rate":   round(self.mutation_rate, 4),
            "regime_bias":     self.regime_bias,
            "timeframe_mix":   self.timeframe_mix,
            "batch_size":      self.batch_size,
            "indicators":      self.indicators,
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
    Analyses historical and live research memory to direct the next
    genome generation cycle.

    Parameters
    ----------
    genome_library:
        ``GenomeLibrary`` instance (from ``router.genome_library``).
    research_grid:
        ``ResearchGrid`` instance (from ``router.research_grid``).
        Provides access to the live ``ResultStore``.
    performance_store:
        ``PerformanceStore`` instance for live trade statistics.
    regime_engine:
        Any engine exposing ``detect_regime()`` or ``get_regime_state()``
        (``RegimeAICore``, ``RegimeDetector``, …).
    refresh_interval_sec:
        Minimum seconds between full re-analyses.  Calls within the
        cooldown return the cached priorities immediately.
    min_samples_for_confidence:
        Minimum number of evaluated genomes before confidence > 0.
    """

    def __init__(
        self,
        genome_library=None,
        research_grid=None,
        performance_store=None,
        regime_engine=None,
        refresh_interval_sec: float = 60.0,
        min_samples_for_confidence: int = 10,
    ) -> None:
        self._genome_library  = genome_library
        self._research_grid   = research_grid
        self._perf_store      = performance_store
        self._regime_engine   = regime_engine

        self.refresh_interval_sec       = max(1.0, float(refresh_interval_sec))
        self.min_samples_for_confidence = max(1, int(min_samples_for_confidence))

        self._lock: threading.Lock          = threading.Lock()
        self._last_priorities: Optional[ResearchPriorities] = None
        self._last_refresh_ts: float        = 0.0
        self._refresh_count: int            = 0
        self._total_prioritise_calls: int   = 0

        logger.info(
            "MetaResearchAI initialized | refresh_interval=%.0fs min_samples=%d",
            self.refresh_interval_sec, self.min_samples_for_confidence,
        )

    # ── Late injection ────────────────────────────────────────────────────────

    def set_genome_library(self, lib: Any) -> None:
        self._genome_library = lib
        logger.debug("MetaResearchAI: genome_library injected.")

    def set_research_grid(self, grid: Any) -> None:
        self._research_grid = grid
        logger.debug("MetaResearchAI: research_grid injected.")

    def set_performance_store(self, store: Any) -> None:
        self._perf_store = store
        logger.debug("MetaResearchAI: performance_store injected.")

    def set_regime_engine(self, engine: Any) -> None:
        self._regime_engine = engine
        logger.debug("MetaResearchAI: regime_engine injected.")

    # ── Public API ────────────────────────────────────────────────────────────

    def prioritise(self, force: bool = False) -> ResearchPriorities:
        """
        Return current research priorities.

        Performs a full re-analysis if the cache has expired or ``force``
        is ``True``; otherwise returns the cached result immediately.

        This method NEVER raises.
        """
        self._total_prioritise_calls += 1
        now = time.time()

        with self._lock:
            if (
                not force
                and self._last_priorities is not None
                and (now - self._last_refresh_ts) < self.refresh_interval_sec
            ):
                return self._last_priorities

        try:
            priorities = self._run_analysis()
        except Exception as exc:
            logger.warning(
                "MetaResearchAI.prioritise: analysis failed (%s) — returning defaults.", exc,
                exc_info=True,
            )
            priorities = self._safe_defaults()

        with self._lock:
            self._last_priorities    = priorities
            self._last_refresh_ts    = now
            self._refresh_count     += 1

        logger.info(
            "MetaResearchAI priorities | family=%-15s mutation=%.2f "
            "markets=%s confidence=%.2f | %s",
            priorities.focus_family,
            priorities.mutation_rate,
            priorities.explore_markets,
            priorities.confidence,
            priorities.reasoning,
        )
        return priorities

    def get_priorities(self) -> Dict[str, Any]:
        """Return priorities as a plain dict (used by StrategyDiscoveryEngine)."""
        return self.prioritise().to_dict()

    def force_refresh(self) -> ResearchPriorities:
        """Force a full re-analysis regardless of TTL."""
        return self.prioritise(force=True)

    def status(self) -> Dict[str, Any]:
        p = self._last_priorities
        return {
            "total_prioritise_calls": self._total_prioritise_calls,
            "refresh_count":          self._refresh_count,
            "last_refresh_ts":        self._last_refresh_ts,
            "cache_age_sec":          round(time.time() - self._last_refresh_ts, 1),
            "refresh_interval_sec":   self.refresh_interval_sec,
            "last_focus_family":      p.focus_family  if p else None,
            "last_confidence":        p.confidence    if p else 0.0,
            "last_mutation_rate":     p.mutation_rate if p else 0.15,
            "sources": {
                "genome_library":   self._genome_library  is not None,
                "research_grid":    self._research_grid   is not None,
                "performance_store":self._perf_store      is not None,
                "regime_engine":    self._regime_engine   is not None,
            },
        }

    # ── Analysis pipeline ─────────────────────────────────────────────────────

    def _run_analysis(self) -> ResearchPriorities:
        """Orchestrates the full analysis pipeline."""
        genome_stats = self._analyse_genome_library()
        grid_stats   = self._analyse_grid_results()
        perf_stats   = self._analyse_performance()
        regime       = self._analyse_regime()
        return self._synthesise(genome_stats, grid_stats, perf_stats, regime)

    # ── Step 1: Genome Library ────────────────────────────────────────────────

    def _analyse_genome_library(self) -> Dict[str, Any]:
        """
        Reads all stored genomes and returns family-level aggregate stats.

        Returns a dict with:
            total_genomes, family_counts, family_fitness, family_market,
            top_families (sorted best→worst by avg fitness),
            weak_families (avg fitness < 0),
            top_k_genomes
        """
        lib = self._genome_library
        empty: Dict[str, Any] = {
            "total_genomes": 0,
            "family_counts": {},
            "family_fitness": {},
            "family_market": {},
            "top_families": [],
            "weak_families": [],
            "top_k_genomes": [],
            "available": False,
        }
        if lib is None:
            return empty

        try:
            all_ids = lib.list_genomes()
        except Exception:
            return empty

        if not all_ids:
            return {**empty, "available": True}

        family_fitness:   Dict[str, List[float]] = defaultdict(list)
        family_market:    Dict[str, List[str]]   = defaultdict(list)
        family_counts:    Dict[str, int]         = defaultdict(int)
        all_scored: List[Tuple[float, str, Dict]] = []

        for gid in all_ids:
            try:
                g = lib.get_genome(gid)
                if g is None:
                    continue
                family   = _infer_family(g)
                fitness  = float(g.get("fitness_score", g.get("score", 0.0)))
                market   = str(
                    g.get("market_filter_gene", {}).get("asset_class", "unknown")
                    if isinstance(g.get("market_filter_gene"), dict) else "unknown"
                )
                family_counts[family]  += 1
                family_fitness[family].append(fitness)
                family_market[family].append(market)
                all_scored.append((fitness, gid, g))
            except Exception:
                continue

        # Average fitness per family
        avg_family_fitness = {
            fam: round(sum(scores) / len(scores), 4)
            for fam, scores in family_fitness.items()
            if scores
        }

        top_families  = sorted(avg_family_fitness, key=avg_family_fitness.get, reverse=True)
        weak_families = [f for f in top_families if avg_family_fitness[f] < 0.0]

        # Top-5 genomes by fitness
        all_scored.sort(key=lambda x: x[0], reverse=True)
        top_k = [{"genome_id": gid, "fitness": fit} for fit, gid, _ in all_scored[:5]]

        return {
            "total_genomes":  len(all_ids),
            "family_counts":  dict(family_counts),
            "family_fitness": avg_family_fitness,
            "family_market":  {
                f: _mode(markets) for f, markets in family_market.items()
            },
            "top_families":   top_families,
            "weak_families":  weak_families,
            "top_k_genomes":  top_k,
            "available":      True,
        }

    # ── Step 2: Grid ResultStore ──────────────────────────────────────────────

    def _analyse_grid_results(self) -> Dict[str, Any]:
        """
        Reads recent results from the ResearchGrid ResultStore.

        Returns:
            total_results, recent_count, avg_fitness, fitness_trend,
            job_type_breakdown, best_family, worst_family
        """
        empty: Dict[str, Any] = {
            "total_results": 0,
            "recent_count":  0,
            "avg_fitness":   0.0,
            "fitness_trend": 0.0,
            "job_type_breakdown": {},
            "best_family":   None,
            "worst_family":  None,
            "available":     False,
        }
        rg = self._research_grid
        if rg is None:
            return empty

        try:
            store = getattr(rg, "_store", None)
            if store is None:
                return empty
            recent = store.latest(200)
        except Exception:
            return empty

        if not recent:
            return {**empty, "available": True}

        ok_results   = [r for r in recent if getattr(r, "ok", False)]
        fitnesses    = [r.fitness for r in ok_results if hasattr(r, "fitness")]
        job_types: Dict[str, int] = defaultdict(int)
        family_fitness: Dict[str, List[float]] = defaultdict(list)

        for r in ok_results:
            jt = str(getattr(r, "job_type", "UNKNOWN"))
            job_types[jt] += 1
            gid = ""
            if hasattr(r, "result") and isinstance(r.result, dict):
                gid = r.result.get("genome_id", "")
            if gid:
                fam = _infer_family_from_id(gid)
                family_fitness[fam].append(r.fitness)

        # Trend: compare first half vs second half average fitness
        trend = 0.0
        if len(fitnesses) >= 4:
            mid    = len(fitnesses) // 2
            first  = sum(fitnesses[:mid]) / mid
            second = sum(fitnesses[mid:]) / (len(fitnesses) - mid)
            trend  = round(second - first, 4)

        avg_family = {
            f: sum(v) / len(v) for f, v in family_fitness.items() if v
        }
        best_fam  = max(avg_family, key=avg_family.get) if avg_family else None
        worst_fam = min(avg_family, key=avg_family.get) if avg_family else None

        return {
            "total_results":      store.stats().get("total_ok", 0) if hasattr(store, "stats") else len(ok_results),
            "recent_count":       len(ok_results),
            "avg_fitness":        round(sum(fitnesses) / len(fitnesses), 4) if fitnesses else 0.0,
            "fitness_trend":      trend,
            "job_type_breakdown": dict(job_types),
            "best_family":        best_fam,
            "worst_family":       worst_fam,
            "available":          True,
        }

    # ── Step 3: Performance Store ─────────────────────────────────────────────

    def _analyse_performance(self) -> Dict[str, Any]:
        """
        Reads live trade performance stats from PerformanceStore.

        Returns:
            total_strategies, best_strategy, worst_strategy,
            family_win_rates, avg_sharpe, avg_win_rate
        """
        empty: Dict[str, Any] = {
            "total_strategies": 0,
            "best_strategy":    None,
            "worst_strategy":   None,
            "family_win_rates": {},
            "avg_sharpe":       0.0,
            "avg_win_rate":     0.0,
            "available":        False,
        }
        ps = self._perf_store
        if ps is None:
            return empty

        try:
            all_metrics: Dict[str, Dict] = ps.get_all_metrics()
        except Exception:
            return empty

        if not all_metrics:
            return {**empty, "available": True}

        sharpes   = []
        win_rates = []
        family_wins: Dict[str, List[float]] = defaultdict(list)
        best_sid, best_sharpe   = None, -999.0
        worst_sid, worst_sharpe = None,  999.0

        for sid, m in all_metrics.items():
            sh = float(m.get("sharpe",   0.0))
            wr = float(m.get("win_rate", 0.0))
            sharpes.append(sh)
            win_rates.append(wr)
            fam = _infer_family_from_id(sid)
            family_wins[fam].append(wr)
            if sh > best_sharpe:
                best_sharpe, best_sid = sh, sid
            if sh < worst_sharpe:
                worst_sharpe, worst_sid = sh, sid

        return {
            "total_strategies": len(all_metrics),
            "best_strategy":    {"id": best_sid,  "sharpe": best_sharpe}  if best_sid  else None,
            "worst_strategy":   {"id": worst_sid, "sharpe": worst_sharpe} if worst_sid else None,
            "family_win_rates": {
                f: round(sum(v) / len(v), 4) for f, v in family_wins.items() if v
            },
            "avg_sharpe":   round(sum(sharpes)   / len(sharpes),   4) if sharpes   else 0.0,
            "avg_win_rate": round(sum(win_rates) / len(win_rates), 4) if win_rates else 0.0,
            "available":    True,
        }

    # ── Step 4: Regime ────────────────────────────────────────────────────────

    def _analyse_regime(self) -> str:
        """Returns current market regime string (e.g. 'TRENDING')."""
        eng = self._regime_engine
        if eng is None:
            return "UNKNOWN"
        try:
            if hasattr(eng, "get_regime_state"):
                state = eng.get_regime_state()
                return str(state.get("regime", "UNKNOWN")).upper()
            if hasattr(eng, "detect_regime"):
                state = eng.detect_regime({})
                return str(state.get("regime", "UNKNOWN")).upper()
            if hasattr(eng, "last_snapshot"):
                snap = eng.last_snapshot()
                if snap:
                    return str(getattr(snap, "dominant_regime", "UNKNOWN")).upper()
        except Exception as exc:
            logger.debug("MetaResearchAI._analyse_regime: %s", exc)
        return "UNKNOWN"

    # ── Step 5: Synthesise ────────────────────────────────────────────────────

    def _synthesise(
        self,
        genome_stats: Dict[str, Any],
        grid_stats:   Dict[str, Any],
        perf_stats:   Dict[str, Any],
        regime:       str,
    ) -> ResearchPriorities:
        """
        Combine signals from all three memory sources into a single
        ResearchPriorities object.

        Decision logic
        --------------
        focus_family:
          1. If grid identifies a best_family with positive trend → use it.
          2. Else if genome library has top_families → use the leader.
          3. Else use regime affinity table.
          4. Fallback → "momentum".

        mutation_rate:
          Base 0.10.  +0.10 if fitness_trend < 0 (search is stagnating).
          +0.05 if weak_families exist.  –0.05 if trend is strongly positive.
          Clamped to [0.05, 0.50].

        explore_markets:
          Derived from which asset classes appear most in top genomes.
          Falls back to ["NSE", "CRYPTO"].

        batch_size:
          Scales with total genomes evaluated (more history → larger batches),
          capped at 50.

        confidence:
          0 until min_samples reached; then interpolates [0,1] based on
          data richness across all three sources.
        """

        # ── focus_family ──────────────────────────────────────────────────────
        focus_family: str = _REGIME_FAMILY_AFFINITY.get(regime, "momentum")
        family_sources: List[str] = []

        # Signal from grid trend
        if grid_stats["available"] and grid_stats["best_family"] and grid_stats["fitness_trend"] > 0:
            focus_family = grid_stats["best_family"]
            family_sources.append(f"grid_best={focus_family}")

        # Override with genome library if it has more signal
        if genome_stats["available"] and genome_stats["top_families"]:
            lib_leader = genome_stats["top_families"][0]
            lib_fitness = genome_stats["family_fitness"].get(lib_leader, 0.0)
            if lib_fitness > 0.1:
                # Only override if significantly better than current choice
                cur_lib_fitness = genome_stats["family_fitness"].get(focus_family, -99.0)
                if lib_fitness > cur_lib_fitness + 0.05:
                    focus_family = lib_leader
                    family_sources.append(f"lib_leader={focus_family}")

        # Override with perf if live trading shows strong family win-rate
        if perf_stats["available"] and perf_stats["family_win_rates"]:
            best_live_fam = max(perf_stats["family_win_rates"], key=perf_stats["family_win_rates"].get)
            best_wr = perf_stats["family_win_rates"][best_live_fam]
            if best_wr > 55.0:
                focus_family = best_live_fam
                family_sources.append(f"live_wr={best_live_fam}({best_wr:.1f}%)")

        if not family_sources:
            family_sources.append(f"regime={regime}")

        # ── mutation_rate ─────────────────────────────────────────────────────
        mutation_rate = 0.10
        reasons: List[str] = []

        fitness_trend = grid_stats.get("fitness_trend", 0.0) if grid_stats["available"] else 0.0
        if fitness_trend < -0.05:
            mutation_rate += 0.10
            reasons.append("stagnating_fitness(+0.10)")
        elif fitness_trend > 0.10:
            mutation_rate -= 0.05
            reasons.append("improving_fitness(-0.05)")

        weak_fams = genome_stats.get("weak_families", []) if genome_stats["available"] else []
        if len(weak_fams) > 2:
            mutation_rate += 0.05
            reasons.append(f"{len(weak_fams)}_weak_families(+0.05)")

        total_genomes = genome_stats.get("total_genomes", 0) if genome_stats["available"] else 0
        if total_genomes < 20:
            mutation_rate += 0.05      # early exploration boost
            reasons.append("early_stage(+0.05)")

        mutation_rate = round(max(0.05, min(0.50, mutation_rate)), 4)

        # ── explore_markets ───────────────────────────────────────────────────
        explore_markets: List[str] = []
        if genome_stats["available"] and genome_stats["family_market"]:
            # Markets most represented in top families
            fam_mkt = genome_stats["family_market"]
            mkt_from_lib = fam_mkt.get(focus_family, "")
            if mkt_from_lib:
                explore_markets.append(mkt_from_lib.upper())
        if "NSE" not in explore_markets:
            explore_markets.insert(0, "NSE")
        if "CRYPTO" not in explore_markets:
            explore_markets.append("CRYPTO")
        explore_markets = explore_markets[:4]

        # ── timeframe_mix ─────────────────────────────────────────────────────
        if regime in ("TRENDING", "BREAKOUT"):
            timeframe_mix = ["15m", "1h", "1d"]
        elif regime == "VOLATILE":
            timeframe_mix = ["5m", "15m"]
        else:
            timeframe_mix = ["5m", "1h"]

        # ── indicators (ranked) ───────────────────────────────────────────────
        family_inds = _FAMILY_INDICATORS.get(focus_family, ["momentum"])
        # Add complementary indicators from runner-up families
        if genome_stats["available"] and len(genome_stats["top_families"]) > 1:
            runner_up = genome_stats["top_families"][1]
            extra_inds = _FAMILY_INDICATORS.get(runner_up, [])
            for ind in extra_inds:
                if ind not in family_inds:
                    family_inds.append(ind)
        # Always include momentum as a fallback
        if "momentum" not in family_inds:
            family_inds.append("momentum")

        # ── batch_size ────────────────────────────────────────────────────────
        base_batch = 20
        batch_size = min(50, base_batch + total_genomes // 10)

        # ── confidence ────────────────────────────────────────────────────────
        total_recent = grid_stats.get("recent_count", 0) if grid_stats["available"] else 0
        sample_count = total_genomes + total_recent

        if sample_count < self.min_samples_for_confidence:
            confidence = 0.0
        else:
            # Sources contribute independently; combine via weighted average
            src_signals = []
            if genome_stats["available"] and total_genomes > 0:
                src_signals.append(min(1.0, total_genomes / 100.0))
            if grid_stats["available"] and total_recent > 0:
                src_signals.append(min(1.0, total_recent / 50.0))
            if perf_stats["available"] and perf_stats["total_strategies"] > 0:
                src_signals.append(min(1.0, perf_stats["total_strategies"] / 20.0))
            confidence = round(sum(src_signals) / max(1, len(src_signals)), 4) if src_signals else 0.0

        # ── reasoning string ──────────────────────────────────────────────────
        reasoning_parts = [
            f"regime={regime}",
            f"focus={focus_family}({'|'.join(family_sources)})",
            f"mutation={mutation_rate}({'|'.join(reasons) or 'base'})",
            f"samples={sample_count}",
            f"confidence={confidence:.2f}",
        ]
        reasoning = " | ".join(reasoning_parts)

        # ── memory snapshot ───────────────────────────────────────────────────
        memory_snapshot = {
            "genome_library":   {k: v for k, v in genome_stats.items() if k != "top_k_genomes"},
            "grid_results":     grid_stats,
            "performance":      perf_stats,
            "regime":           regime,
        }

        return ResearchPriorities(
            focus_family    = focus_family,
            explore_markets = explore_markets,
            mutation_rate   = mutation_rate,
            regime_bias     = regime,
            timeframe_mix   = timeframe_mix,
            batch_size      = batch_size,
            indicators      = family_inds,
            confidence      = confidence,
            reasoning       = reasoning,
            generated_at    = time.time(),
            memory_snapshot = memory_snapshot,
        )

    def _safe_defaults(self) -> ResearchPriorities:
        """Return safe default priorities on any analysis failure."""
        return ResearchPriorities(
            focus_family    = "momentum",
            explore_markets = ["NSE", "CRYPTO"],
            mutation_rate   = 0.15,
            regime_bias     = "UNKNOWN",
            timeframe_mix   = ["5m", "1h"],
            batch_size      = 20,
            indicators      = ["momentum", "mean_reversion", "rsi", "breakout"],
            confidence      = 0.0,
            reasoning       = "safe_defaults — analysis failed",
            generated_at    = time.time(),
            memory_snapshot = {},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _infer_family(genome: Dict[str, Any]) -> str:
    """Infer strategy family from a genome dict."""
    # Direct field
    if "family" in genome:
        return str(genome["family"]).lower()

    # Signal gene type/indicator
    sg = genome.get("signal_gene") or {}
    if isinstance(sg, dict):
        indicator = str(sg.get("indicator", sg.get("type", ""))).lower()
        if indicator:
            for fam, inds in _FAMILY_INDICATORS.items():
                if indicator in inds:
                    return fam
            # Direct name match
            if indicator in _FAMILY_INDICATORS:
                return indicator

    # genome_id prefix heuristic
    gid = str(genome.get("genome_id", "")).lower()
    for fam in _FAMILY_INDICATORS:
        if fam in gid:
            return fam

    return "momentum"


def _infer_family_from_id(identifier: str) -> str:
    """Infer family from a strategy or genome ID string."""
    lower = str(identifier).lower()
    for fam in _FAMILY_INDICATORS:
        if fam in lower:
            return fam
    return "momentum"


def _mode(values: list) -> str:
    """Return most common element in a list."""
    if not values:
        return ""
    counts: Dict[str, int] = defaultdict(int)
    for v in values:
        counts[str(v)] += 1
    return max(counts, key=counts.get)
