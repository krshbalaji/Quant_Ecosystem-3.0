"""
strategy_discovery_engine.py — Quant Ecosystem 3.0
=====================================================

Production-grade strategy discovery engine with Meta-Research AI guidance.

Architecture
------------

  MetaResearchAI                   ← analyses ResearchMemory each cycle
       │  prioritise() → ResearchPriorities
       ↓
  StrategyDiscoveryEngine          ← consults priorities before generation
       │
       ├── _generate_genomes(count, priorities)
       │       └── biases random sampling toward focus_family,
       │           preferred indicators, mutation_rate, timeframe_mix
       │
       ├── _evaluate_parallel(genomes, symbols)
       │       └─► ResearchGrid.submit_genome_sweep()   (CPU-parallel)
       │
       └── _evaluate_local(genomes)
               └─► BacktestEngine.run()   (single-threaded fallback)

MetaResearchAI integration
--------------------------
  1. On every discover() call, ask MetaResearchAI for current priorities.
  2. Apply priorities to genome generation:
       • focus_family     → over-sample the top-performing family
       • indicators       → restrict/rank indicator sampling
       • mutation_rate    → interpolate random vs mutated genomes
       • timeframe_mix    → weight timeframe sampling
       • explore_markets  → filter symbols list
       • batch_size       → clamp or expand batch
  3. If MetaResearchAI is unavailable or raises, fall back to the plain
     random generator — no exception propagates.

Injection pattern
-----------------
  SystemFactory._boot_research_memory() creates engine with meta_research_ai=None.
  SystemFactory._boot_meta_research()   calls set_meta_research_ai() once ready.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Strategy families and their canonical indicators — matches MetaResearchAI
_FAMILY_INDICATORS: Dict[str, List[str]] = {
    "trend":          ["momentum", "ma_cross"],
    "mean_reversion": ["mean_reversion", "rsi"],
    "breakout":       ["breakout", "volatility_breakout"],
    "volatility":     ["volatility_breakout"],
    "stat_arb":       ["mean_reversion", "rsi"],
    "momentum":       ["momentum", "ma_cross"],
    "oscillator":     ["rsi"],
}
_ALL_INDICATORS = [
    "momentum", "mean_reversion", "rsi", "ma_cross",
    "breakout", "volatility_breakout",
]
_ALL_TIMEFRAMES  = ["5m", "15m", "1h", "4h", "1d"]


class StrategyDiscoveryEngine:
    """
    Generates and evaluates candidate strategy genomes.

    Parameters
    ----------
    dataset_builder:
        ResearchDatasetBuilder for historical feature data.
    factor_builder:
        FactorDatasetBuilder for cross-sectional factor signals.
    distributed_engine:
        Legacy DistributedResearchEngine (kept for backward compatibility).
    research_grid:
        ResearchGrid instance for CPU-parallel evaluation.
    meta_research_ai:
        MetaResearchAI instance.  Consulted before every genome generation
        batch to bias sampling toward high-potential families/indicators.
        If ``None``, plain random generation is used.
    max_new_strategies:
        Default genome batch size per discover() call.
    wait_timeout_sec:
        Seconds to block for parallel jobs before returning partial results.
    """

    def __init__(
        self,
        dataset_builder=None,
        factor_builder=None,
        distributed_engine=None,
        research_grid=None,
        meta_research_ai=None,
        max_new_strategies: int = 20,
        wait_timeout_sec: float = 60.0,
    ) -> None:
        self.dataset_builder    = dataset_builder
        self.factor_builder     = factor_builder
        self.distributed_engine = distributed_engine
        self._research_grid     = research_grid
        self._meta_research_ai  = meta_research_ai
        self.max_new_strategies = max(1, int(max_new_strategies))
        self.wait_timeout_sec   = float(wait_timeout_sec)

        # Diagnostics
        self._total_genomes_submitted = 0
        self._total_genomes_promoted  = 0
        self._total_discover_calls    = 0
        self._last_job_ids: List[str] = []
        self._last_priorities: Optional[Dict] = None

        logger.info(
            "StrategyDiscoveryEngine initialized | max_batch=%d grid=%s meta_ai=%s",
            self.max_new_strategies,
            "yes" if research_grid is not None else "no",
            "yes" if meta_research_ai is not None else "no",
        )

    # ── Late injection ─────────────────────────────────────────────────────────

    def set_research_grid(self, grid: Any) -> None:
        """Inject (or replace) the ResearchGrid after construction."""
        prev = self._research_grid
        self._research_grid = grid
        if grid is not None:
            logger.info(
                "StrategyDiscoveryEngine: ResearchGrid injected "
                "(workers=%d pool=%s) — parallel evaluation active.",
                getattr(grid, "_n_workers", "?"),
                getattr(getattr(grid, "_pool", None), "pool_type", "?"),
            )
        elif prev is not None:
            logger.info(
                "StrategyDiscoveryEngine: ResearchGrid removed — "
                "reverting to single-threaded evaluation."
            )

    def set_meta_research_ai(self, meta_ai: Any) -> None:
        """
        Inject (or replace) the MetaResearchAI after construction.

        Called by ``SystemFactory._boot_meta_research()`` once the AI layer
        has been started and confirmed healthy.
        """
        prev = self._meta_research_ai
        self._meta_research_ai = meta_ai
        if meta_ai is not None:
            logger.info(
                "StrategyDiscoveryEngine: MetaResearchAI injected — "
                "data-driven genome guidance active."
            )
        elif prev is not None:
            logger.info(
                "StrategyDiscoveryEngine: MetaResearchAI removed — "
                "reverting to random genome generation."
            )

    # ── Main entry point ───────────────────────────────────────────────────────

    def discover(
        self,
        count: int = 0,
        symbols: Optional[List[str]] = None,
        wait: bool = True,
    ) -> List[Dict]:
        """
        Consult MetaResearchAI for priorities, generate guided genomes,
        then evaluate them in parallel (or locally as fallback).

        Parameters
        ----------
        count:
            Genome batch size.  If 0, uses ``max_new_strategies``
            (or MetaResearchAI's recommended ``batch_size``).
        symbols:
            Symbols to test against.  If None, MetaResearchAI's
            ``explore_markets`` list is used; falls back to ["SYNTH"].
        wait:
            Block until parallel jobs finish (up to ``wait_timeout_sec``).
        """
        self._total_discover_calls += 1

        # ── Step 1: Consult MetaResearchAI ────────────────────────────────────
        priorities = self._get_priorities()
        self._last_priorities = priorities

        # Resolve batch count — MetaResearchAI may recommend a larger batch
        if count > 0:
            n = count
        else:
            n = max(self.max_new_strategies, priorities.get("batch_size", self.max_new_strategies))

        # Resolve symbols — MetaResearchAI recommends which markets to explore
        if symbols is not None:
            syms = symbols
        else:
            markets = priorities.get("explore_markets") or []
            syms = _markets_to_symbols(markets) or ["SYNTH"]

        logger.info(
            "StrategyDiscoveryEngine.discover | genomes=%d symbols=%s "
            "family=%s mutation=%.2f grid=%s meta_ai=%s",
            n, syms,
            priorities.get("focus_family", "?"),
            priorities.get("mutation_rate", 0.15),
            "yes" if self._research_grid is not None else "no",
            "yes" if self._meta_research_ai is not None else "no",
        )

        # ── Step 2: Generate genomes guided by priorities ─────────────────────
        genomes = self._generate_genomes(n, priorities)
        if not genomes:
            logger.warning("StrategyDiscoveryEngine.discover: no genomes generated.")
            return []

        # ── Step 3: Evaluate ──────────────────────────────────────────────────
        if self._research_grid is not None:
            return self._evaluate_parallel(genomes, syms, wait=wait)
        return self._evaluate_local(genomes)

    def generate(
        self,
        count: int = 0,
        symbols: Optional[List[str]] = None,
        wait: bool = True,
    ) -> List[Dict]:
        """Alias for ``discover()``."""
        return self.discover(count=count, symbols=symbols, wait=wait)

    # ── MetaResearchAI consultation ────────────────────────────────────────────

    def _get_priorities(self) -> Dict:
        """
        Ask MetaResearchAI for current research priorities.

        Returns a plain dict with safe defaults if the AI is unavailable
        or raises.  Never propagates an exception.
        """
        _defaults = {
            "focus_family":    "momentum",
            "explore_markets": ["NSE", "CRYPTO"],
            "mutation_rate":   0.15,
            "batch_size":      self.max_new_strategies,
            "indicators":      _ALL_INDICATORS,
            "timeframe_mix":   ["5m", "1h"],
            "regime_bias":     "UNKNOWN",
            "confidence":      0.0,
        }

        meta = self._meta_research_ai
        if meta is None:
            return _defaults

        try:
            p = meta.get_priorities()     # returns a plain dict
            # Merge with defaults for any missing keys
            return {**_defaults, **p}
        except Exception as exc:
            logger.debug(
                "StrategyDiscoveryEngine._get_priorities: MetaResearchAI failed (%s) "
                "— using defaults.", exc,
            )
            return _defaults

    # ── Guided genome generation ────────────────────────────────────────────────

    def _generate_genomes(self, count: int, priorities: Dict) -> List[Dict]:
        """
        Build ``count`` candidate genomes biased by MetaResearchAI priorities.

        Allocation strategy
        -------------------
        mutation_rate (e.g. 0.15) controls the fraction of genomes that are
        mutations of existing library genomes vs fresh random ones.

        focus_family  controls which signal indicator pool is sampled.
        indicators    provides the ordered list of indicators to draw from.
        timeframe_mix weights the timeframe sampling.
        """
        focus_family  = str(priorities.get("focus_family",  "momentum"))
        indicators    = list(priorities.get("indicators",   _ALL_INDICATORS) or _ALL_INDICATORS)
        timeframes    = list(priorities.get("timeframe_mix",["5m", "1h"])   or ["5m", "1h"])
        mutation_rate = float(priorities.get("mutation_rate", 0.15))

        # Number of slots allocated to each strategy
        n_mutated  = max(0, int(count * mutation_rate))
        n_focused  = max(1, int((count - n_mutated) * 0.6))  # 60% → focus family
        n_random   = max(0, count - n_mutated - n_focused)    # rest → pure random

        logger.debug(
            "_generate_genomes | total=%d focused=%d random=%d mutated=%d "
            "family=%s indicators=%s",
            count, n_focused, n_random, n_mutated,
            focus_family, indicators[:4],
        )

        genomes: List[Dict] = []

        # ── Focused genomes (family-biased) ───────────────────────────────────
        family_inds = _FAMILY_INDICATORS.get(focus_family, indicators[:2])
        # Add extra indicators from the priority list if the family set is small
        for ind in indicators:
            if ind not in family_inds:
                family_inds.append(ind)

        for _ in range(n_focused):
            genomes.append(self._guided_genome(
                indicator_pool=family_inds,
                family=focus_family,
                timeframe_pool=timeframes,
            ))

        # ── Pure random genomes ───────────────────────────────────────────────
        for _ in range(n_random):
            genomes.append(self._random_genome())

        # ── Mutated genomes from GenomeLibrary ────────────────────────────────
        if n_mutated > 0:
            mutated = self._generate_mutated(n_mutated, focus_family, timeframes)
            genomes.extend(mutated)
            logger.debug("Generated %d mutated genomes.", len(mutated))

        return genomes[:count]

    def _guided_genome(
        self,
        indicator_pool: List[str],
        family: str,
        timeframe_pool: List[str],
    ) -> Dict:
        """Generate a single genome biased toward a specific family/indicator set."""
        rng       = random.Random()
        now       = time.strftime("%Y%m%d_%H%M%S")
        indicator = rng.choice(indicator_pool) if indicator_pool else "momentum"
        tf        = rng.choice(timeframe_pool) if timeframe_pool else "1h"
        genome_id = f"meta_{family[:6]}_{indicator[:6]}_{now}_{uuid.uuid4().hex[:6]}"

        return {
            "genome_id": genome_id,
            "family": family,
            "source": "meta_guided",
            "signal_gene": {
                "indicator":   indicator,
                "threshold":   round(rng.uniform(0.001, 0.02), 5),
                "lookback":    rng.randint(8, 60),
                "slow_period": rng.randint(20, 100),
            },
            "risk_gene": {
                "risk_pct":      round(rng.uniform(0.5, 2.0), 3),
                "stop_loss_pct": round(rng.uniform(0.5, 3.0), 3),
            },
            "execution_gene": {
                "slippage_bps_limit": round(rng.uniform(3.0, 15.0), 1),
                "timeframe": tf,
            },
            "market_filter_gene": {
                "volatility_min": round(rng.uniform(0.08, 0.35), 4),
                "session":        rng.choice(["ALL", "REGULAR", "HIGH_LIQ"]),
                "asset_class":    rng.choice(["stocks", "indices", "forex", "crypto"]),
            },
        }

    def _random_genome(self) -> Dict:
        """Fully random genome — no MetaResearchAI guidance."""
        rng         = random.Random()
        now         = time.strftime("%Y%m%d_%H%M%S")
        signal_type = rng.choice(_ALL_INDICATORS)
        tf          = rng.choice(_ALL_TIMEFRAMES)
        genome_id   = f"disc_{signal_type}_{now}_{uuid.uuid4().hex[:6]}"

        return {
            "genome_id": genome_id,
            "family": signal_type,
            "source": "random",
            "signal_gene": {
                "indicator":   signal_type,
                "threshold":   round(rng.uniform(0.001, 0.02), 5),
                "lookback":    rng.randint(8, 60),
                "slow_period": rng.randint(20, 100),
            },
            "risk_gene": {
                "risk_pct":      round(rng.uniform(0.5, 2.0), 3),
                "stop_loss_pct": round(rng.uniform(0.5, 3.0), 3),
            },
            "execution_gene": {
                "slippage_bps_limit": round(rng.uniform(3.0, 15.0), 1),
                "timeframe": tf,
            },
            "market_filter_gene": {
                "volatility_min": round(rng.uniform(0.08, 0.35), 4),
                "session":        rng.choice(["ALL", "REGULAR", "HIGH_LIQ"]),
                "asset_class":    rng.choice(["stocks", "indices", "forex", "crypto"]),
            },
        }

    def _generate_mutated(
        self,
        count: int,
        focus_family: str,
        timeframes: List[str],
    ) -> List[Dict]:
        """
        Pull high-fitness genomes from the library and return mutated variants.
        Falls back to guided random genomes if the library is empty or unavailable.
        """
        lib = getattr(self, "_genome_library", None)
        if lib is None:
            # Try to reach through research_grid's genome_library reference
            rg = self._research_grid
            if rg is not None:
                lib = getattr(rg, "_genome_library", None)

        if lib is None:
            # No library — return focused randoms instead
            return [self._guided_genome(
                indicator_pool=_FAMILY_INDICATORS.get(focus_family, _ALL_INDICATORS[:2]),
                family=focus_family,
                timeframe_pool=timeframes,
            ) for _ in range(count)]

        try:
            all_ids = lib.list_genomes()
        except Exception:
            all_ids = []

        if not all_ids:
            return [self._guided_genome(
                indicator_pool=_FAMILY_INDICATORS.get(focus_family, _ALL_INDICATORS[:2]),
                family=focus_family,
                timeframe_pool=timeframes,
            ) for _ in range(count)]

        # Sample a few parent genomes (prefer family-matching ones)
        rng = random.Random()
        family_ids   = [gid for gid in all_ids if focus_family in gid.lower()]
        parent_pool  = family_ids if family_ids else all_ids
        parents      = rng.sample(parent_pool, min(count, len(parent_pool)))

        mutated: List[Dict] = []
        for parent_id in parents:
            try:
                parent = lib.get_genome(parent_id)
                if parent is None:
                    continue
                child = _mutate_genome(parent, rng, timeframes)
                mutated.append(child)
            except Exception:
                mutated.append(self._guided_genome(
                    indicator_pool=_FAMILY_INDICATORS.get(focus_family, _ALL_INDICATORS[:2]),
                    family=focus_family,
                    timeframe_pool=timeframes,
                ))

        # Pad to requested count if we didn't get enough parents
        while len(mutated) < count:
            mutated.append(self._guided_genome(
                indicator_pool=_FAMILY_INDICATORS.get(focus_family, _ALL_INDICATORS[:2]),
                family=focus_family,
                timeframe_pool=timeframes,
            ))

        return mutated[:count]

    # ── Parallel evaluation via ResearchGrid ───────────────────────────────────

    def _evaluate_parallel(
        self,
        genomes: List[Dict],
        symbols: List[str],
        wait: bool = True,
    ) -> List[Dict]:
        """Submit genomes to ResearchGrid and optionally wait for results."""
        grid = self._research_grid
        if grid is None:
            return self._evaluate_local(genomes)

        try:
            job_ids = grid.submit_genome_sweep(
                genomes,
                symbols=symbols,
                periods=260,
                priority=50,
            )
            self._last_job_ids = job_ids
            self._total_genomes_submitted += len(genomes)

            logger.info(
                "StrategyDiscoveryEngine: submitted %d genomes | jobs=%d | symbols=%s",
                len(genomes), len(job_ids), symbols,
            )

            if not wait:
                return []

            n_done = grid._wait_for_jobs(job_ids, timeout_sec=self.wait_timeout_sec)
            logger.info(
                "StrategyDiscoveryEngine: %d/%d jobs completed.",
                n_done, len(job_ids),
            )

            evaluated: List[Dict] = []
            for jid in job_ids:
                result = grid.get_result(jid)
                if result is not None and result.ok:
                    evaluated.append(result.result or {})

            n_prom = grid.auto_promote()
            if n_prom > 0:
                self._total_genomes_promoted += n_prom
                logger.info(
                    "StrategyDiscoveryEngine: %d genomes promoted to GenomeLibrary.",
                    n_prom,
                )

            return evaluated

        except Exception as exc:
            logger.warning(
                "StrategyDiscoveryEngine._evaluate_parallel failed (%s) — "
                "falling back to local evaluation.", exc,
            )
            return self._evaluate_local(genomes)

    # ── Single-threaded fallback evaluation ───────────────────────────────────

    def _evaluate_local(self, genomes: List[Dict]) -> List[Dict]:
        """Single-threaded BacktestEngine evaluation — always available."""
        logger.debug(
            "StrategyDiscoveryEngine._evaluate_local: %d genomes.", len(genomes),
        )
        results: List[Dict] = []

        try:
            from quant_ecosystem.research.backtest.backtest_engine import (  # noqa: PLC0415
                BacktestEngine,
            )
            engine = BacktestEngine()
        except Exception as exc:
            logger.debug("BacktestEngine unavailable: %s", exc)
            for g in genomes:
                g.setdefault("fitness_score", 0.0)
                g.setdefault("sharpe", 0.0)
            return genomes

        for genome in genomes:
            try:
                result = engine.run(
                    _genome_to_callable(genome),
                    data=120,
                    symbol="SYNTH",
                )
                m   = result.metrics
                row = dict(genome)
                row.update({
                    "sharpe":        m.get("sharpe",          0.0),
                    "max_dd":        m.get("max_dd",          0.0),
                    "win_rate":      m.get("win_rate",        0.0),
                    "profit_factor": m.get("profit_factor",   0.0),
                    "total_return":  m.get("total_return_pct",0.0),
                    "fitness_score": _fitness(m),
                })
                results.append(row)
                logger.debug(
                    "local eval | %s sharpe=%+.3f fitness=%+.3f",
                    genome.get("genome_id", "?")[:16],
                    row["sharpe"], row["fitness_score"],
                )
            except Exception as exc:
                logger.debug("local eval error %s: %s", genome.get("genome_id","?"), exc)
                g = dict(genome)
                g.setdefault("fitness_score", -1.0)
                g.setdefault("sharpe", 0.0)
                results.append(g)

        return results

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        grid = self._research_grid
        meta = self._meta_research_ai
        return {
            "mode":                    "parallel" if grid else "single_threaded",
            "grid_active":             grid is not None,
            "meta_ai_active":          meta is not None,
            "total_discover_calls":    self._total_discover_calls,
            "total_genomes_submitted": self._total_genomes_submitted,
            "total_genomes_promoted":  self._total_genomes_promoted,
            "last_job_ids":            len(self._last_job_ids),
            "last_priorities":         self._last_priorities or {},
            "grid_status":             grid.status() if grid else {},
            "meta_ai_status":          meta.status() if meta else {},
        }

    # ── Legacy ────────────────────────────────────────────────────────────────

    def _generate_strategy(self) -> Optional[Dict]:
        return self._random_genome()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers (safe in worker processes — no class state)
# ─────────────────────────────────────────────────────────────────────────────

def _fitness(m: Dict) -> float:
    s  = float(m.get("sharpe",        0.0))
    dd = float(m.get("max_dd",        0.0))
    wr = float(m.get("win_rate",      0.0))
    pf = float(m.get("profit_factor", 0.0))
    return max(-2.0, min(2.0,
        s * 0.40 + (wr / 100.0 - 0.5) * 2.0 * 0.20 + (pf - 1.0) * 0.25 - dd * 0.005
    ))


def _mutate_genome(genome: Dict, rng: random.Random, timeframes: List[str]) -> Dict:
    """Return a lightly mutated copy of a parent genome."""
    child    = {k: (dict(v) if isinstance(v, dict) else v) for k, v in genome.items()}
    gid_base = str(genome.get("genome_id", "parent"))
    child["genome_id"] = f"mut_{gid_base[:12]}_{uuid.uuid4().hex[:6]}"
    child["source"]    = "mutation"
    child.pop("fitness_score", None)
    child.pop("sharpe",        None)

    sg = child.get("signal_gene")
    if isinstance(sg, dict):
        if rng.random() < 0.5:
            sg["threshold"] = round(sg.get("threshold", 0.005) * rng.uniform(0.7, 1.4), 6)
        if rng.random() < 0.5:
            sg["lookback"]  = max(5, min(200, int(sg.get("lookback", 20) * rng.uniform(0.6, 1.6))))

    rk = child.get("risk_gene")
    if isinstance(rk, dict):
        if rng.random() < 0.4:
            rk["risk_pct"]      = round(rk.get("risk_pct", 1.0) * rng.uniform(0.8, 1.3), 3)
        if rng.random() < 0.4:
            rk["stop_loss_pct"] = round(rk.get("stop_loss_pct", 1.5) * rng.uniform(0.8, 1.3), 3)

    ex = child.get("execution_gene")
    if isinstance(ex, dict) and timeframes and rng.random() < 0.3:
        ex["timeframe"] = rng.choice(timeframes)

    return child


def _markets_to_symbols(markets: List[str]) -> List[str]:
    """Convert MetaResearchAI market names to synthetic symbol tokens."""
    mapping = {
        "NSE":         ["NSE:INFY", "NSE:RELIANCE", "NSE:TCS"],
        "CRYPTO":      ["BTC:USDT", "ETH:USDT"],
        "FOREX":       ["EUR:USD", "GBP:USD"],
        "INDICES":     ["NIFTY:50", "SPX:500"],
        "COMMODITIES": ["GOLD:USD", "CRUDE:USD"],
    }
    symbols: List[str] = []
    for market in (markets or []):
        symbols.extend(mapping.get(str(market).upper(), []))
    # Always include at least one synthetic fallback
    if not symbols:
        symbols = ["SYNTH"]
    return symbols


def _genome_to_callable(genome: Dict) -> Callable:
    """Build a strategy callable from a genome dict."""
    sg        = genome.get("signal_gene", {}) or {}
    indicator = str(sg.get("indicator", "momentum")).lower()
    threshold = float(sg.get("threshold", 0.005))
    period    = max(5, min(int(sg.get("lookback", sg.get("period", 20))), 200))

    def _strategy(window: Dict) -> str:
        closes = window.get("close", [])
        if hasattr(closes, "tolist"):
            closes = closes.tolist()
        if len(closes) < period + 2:
            return "HOLD"
        try:
            c = [float(x) for x in closes]
            if indicator == "momentum":
                sig = (c[-1] - c[-period]) / max(abs(c[-period]), 1e-9)
                return "BUY" if sig > threshold else ("SELL" if sig < -threshold else "HOLD")
            elif indicator in ("rsi", "oscillator"):
                gains  = [max(c[i]-c[i-1], 0) for i in range(len(c)-period, len(c))]
                losses = [max(c[i-1]-c[i], 0) for i in range(len(c)-period, len(c))]
                ag, al = sum(gains)/period, sum(losses)/period
                rsi    = 100 - 100/(1 + (ag/al if al > 0 else 100.0))
                thr    = float(threshold) if threshold > 1 else 50.0
                return "BUY" if rsi < thr else ("SELL" if rsi > (100-thr) else "HOLD")
            elif indicator in ("ma_cross", "ema_cross", "trend"):
                slow    = max(period+1, min(int(sg.get("slow_period", period*2)), len(c)-2))
                fast_ma = sum(c[-period:]) / period
                slow_ma = sum(c[-slow:])   / slow
                prev_f  = sum(c[-period-1:-1]) / period
                prev_s  = sum(c[-slow-1:-1])   / slow
                if prev_f <= prev_s and fast_ma > slow_ma: return "BUY"
                if prev_f >= prev_s and fast_ma < slow_ma: return "SELL"
                return "HOLD"
            elif indicator == "breakout":
                hi   = max(c[-period-1:-1])
                lo   = min(c[-period-1:-1])
                thr2 = max(threshold, 0.001)
                if c[-1] > hi*(1+thr2): return "BUY"
                if c[-1] < lo*(1-thr2): return "SELL"
                return "HOLD"
            elif indicator in ("mean_reversion", "stat_arb"):
                ma   = sum(c[-period:]) / period
                std_ = (sum((x-ma)**2 for x in c[-period:]) / period)**0.5
                z    = (c[-1] - ma) / (std_ + 1e-9)
                thr3 = float(threshold) if threshold > 0.01 else 1.5
                return "SELL" if z > thr3 else ("BUY" if z < -thr3 else "HOLD")
            elif indicator in ("volatility_breakout", "volatility"):
                atr  = sum(abs(c[i]-c[i-1]) for i in range(-period, 0)) / period
                thr4 = max(float(threshold), 0.5)
                if c[-1] > c[-2] + atr*thr4: return "BUY"
                if c[-1] < c[-2] - atr*thr4: return "SELL"
                return "HOLD"
        except Exception:
            pass
        return "HOLD"

    return _strategy
