"""
parallel_research_grid.py — Quant Ecosystem 3.0
==================================================

Production-grade parallel research grid for strategy discovery.

Architecture
------------

                          ┌──────────────────────────────────────────┐
                          │            ResearchGrid                  │
                          │  (public API — submit, results, promote) │
                          └────────────┬─────────────────────────────┘
                                       │
                          ┌────────────▼─────────────────────────────┐
                          │         GridScheduler                    │
                          │  (priority queue, dedup, rate-limit)     │
                          └────────────┬─────────────────────────────┘
                                       │
               ┌───────────────────────┼───────────────────────┐
               ▼                       ▼                       ▼
    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │  ProcessPool     │   │  ThreadPool      │   │  InlineWorker    │
    │  (CPU-bound:     │   │  (I/O-bound:     │   │  (fallback when  │
    │   backtest,      │   │   shadow, fetch, │   │   fork unsafe)   │
    │   parameter      │   │   genome store)  │   │                  │
    │   sweep, MC)     │   │                  │   │                  │
    └──────────────────┘   └──────────────────┘   └──────────────────┘
               │                       │
               └───────────┬───────────┘
                           ▼
               ┌──────────────────────┐
               │   ResultStore        │
               │  (thread-safe,       │
               │   ranked, ring-buf)  │
               └──────────────────────┘

Job types
---------
GENOME_BACKTEST     — backtest a single genome / strategy callable
GENOME_SWEEP        — backtest N genomes × M symbols in parallel
PARAMETER_SWEEP     — grid search over a param dict
WALK_FORWARD_BATCH  — run walk-forward for multiple strategies in parallel
MONTE_CARLO         — N randomised runs of a strategy for robustness
FACTOR_BACKTEST     — build and backtest factor-based signals
SHADOW_EVAL         — replay shadow portfolio for a strategy
CROSS_VALIDATION    — k-fold cross-validation on a dataset

All job types are CPU-bound and dispatched to the process pool.
Dependency injection is used throughout — no module-level external imports.

Design constraints
------------------
- Zero module-level third-party imports.
- Runs in PAPER mode with zero external services (synthetic data fallback).
- Integrates with SystemFactory via constructor injection.
- Process pool uses ``spawn`` context (safe on all OSes, including macOS).
- Falls back to thread pool if ``spawn`` is unavailable.
- All public methods return immediately and optionally accept callbacks.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
import uuid
from collections import deque
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from queue import Empty, PriorityQueue
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class JobType(str, Enum):
    GENOME_BACKTEST    = "GENOME_BACKTEST"
    GENOME_SWEEP       = "GENOME_SWEEP"
    PARAMETER_SWEEP    = "PARAMETER_SWEEP"
    WALK_FORWARD_BATCH = "WALK_FORWARD_BATCH"
    MONTE_CARLO        = "MONTE_CARLO"
    FACTOR_BACKTEST    = "FACTOR_BACKTEST"
    SHADOW_EVAL        = "SHADOW_EVAL"
    CROSS_VALIDATION   = "CROSS_VALIDATION"


class JobStatus(str, Enum):
    QUEUED     = "QUEUED"
    RUNNING    = "RUNNING"
    DONE       = "DONE"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"


# ---------------------------------------------------------------------------
# Job / Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(order=True)
class GridJob:
    """A unit of parallel research work."""

    # Priority first for heap ordering (lower = higher priority)
    priority:     int                        = field(default=50, compare=True)
    created_ts:   float                      = field(default_factory=time.time, compare=True)
    job_id:       str                        = field(default_factory=lambda: uuid.uuid4().hex, compare=False)
    job_type:     JobType                    = field(default=JobType.GENOME_BACKTEST,  compare=False)
    payload:      Dict[str, Any]             = field(default_factory=dict,             compare=False)
    status:       JobStatus                  = field(default=JobStatus.QUEUED,         compare=False)
    submitted_by: str                        = field(default="",                       compare=False)
    max_retries:  int                        = field(default=1,                        compare=False)
    retries:      int                        = field(default=0,                        compare=False)
    tags:         Dict[str, str]             = field(default_factory=dict,             compare=False)
    timeout_sec:  float                      = field(default=120.0,                    compare=False)


@dataclass
class GridResult:
    """Outcome of a single grid job."""

    job_id:       str
    job_type:     JobType
    ok:           bool
    payload:      Dict[str, Any]       # original job payload (small subset)
    result:       Dict[str, Any]       # computed result
    error:        Optional[str]        = None
    elapsed_sec:  float                = 0.0
    worker_pid:   int                  = 0
    completed_ts: float                = field(default_factory=time.time)

    # Convenience metrics extracted from result for quick ranking
    sharpe:        float = 0.0
    max_dd:        float = 0.0
    profit_factor: float = 0.0
    win_rate:      float = 0.0
    fitness:       float = 0.0

    def __post_init__(self) -> None:
        if self.ok and self.result:
            self.sharpe        = float(self.result.get("sharpe",        0.0))
            self.max_dd        = float(self.result.get("max_dd",        0.0))
            self.profit_factor = float(self.result.get("profit_factor", 0.0))
            self.win_rate      = float(self.result.get("win_rate",      0.0))
            self.fitness       = float(self.result.get("fitness_score", 0.0))


# ---------------------------------------------------------------------------
# Pure functions — executed inside worker processes (no class state)
# ---------------------------------------------------------------------------
# These MUST be module-level so ProcessPoolExecutor can pickle them.

def _run_genome_backtest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: backtest a single genome / strategy callable."""
    import random as _rnd
    import math as _m

    genome      = payload.get("genome", {})
    candles     = payload.get("candles") or []
    periods     = int(payload.get("periods", 260))
    slip_bps    = float(payload.get("slippage_bps", 5.0))
    commission  = float(payload.get("commission", 20.0))

    try:
        from quant_ecosystem.research.backtest.backtest_engine import (  # noqa: lazy
            BacktestEngine, FixedBpsSlippage, FlatCommission
        )
        engine = BacktestEngine(
            slippage_model  = FixedBpsSlippage(slip_bps),
            commission_model= FlatCommission(commission),
        )
        if candles:
            data = candles
        else:
            data = periods

        strategy = _genome_to_callable(genome)
        result   = engine.run(strategy, data, symbol=str(payload.get("symbol", "GRID")))
        m = result.metrics
        return {
            "genome_id":    genome.get("genome_id", payload.get("genome_id", "")),
            "symbol":       payload.get("symbol", "GRID"),
            "sharpe":       m.get("sharpe",         0.0),
            "max_dd":       m.get("max_dd",          0.0),
            "win_rate":     m.get("win_rate",        0.0),
            "profit_factor":m.get("profit_factor",   0.0),
            "total_return": m.get("total_return_pct",0.0),
            "total_trades": m.get("total_trades",    0),
            "fitness_score":_fitness(m),
            "periods":      periods,
        }
    except Exception as exc:
        return {"error": str(exc), "genome_id": genome.get("genome_id", ""), "sharpe": 0.0, "fitness_score": -1.0}


def _run_genome_sweep(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: backtest a genome across multiple symbols."""
    genome   = payload.get("genome", {})
    symbols  = payload.get("symbols") or ["SYNTH"]
    periods  = int(payload.get("periods", 260))
    slip_bps = float(payload.get("slippage_bps", 5.0))
    comm     = float(payload.get("commission", 20.0))

    results = []
    for sym in symbols:
        r = _run_genome_backtest({
            "genome":        genome,
            "symbol":        sym,
            "periods":       periods,
            "slippage_bps":  slip_bps,
            "commission":    comm,
        })
        results.append(r)

    if not results:
        return {"genome_id": genome.get("genome_id",""), "results": [], "avg_sharpe": 0.0, "fitness_score": -1.0}

    ok   = [r for r in results if "error" not in r]
    avg_sharpe = sum(r["sharpe"] for r in ok) / len(ok) if ok else 0.0
    avg_fitness= sum(r["fitness_score"] for r in ok) / len(ok) if ok else -1.0

    return {
        "genome_id":  genome.get("genome_id", ""),
        "symbols":    symbols,
        "n_symbols":  len(symbols),
        "results":    results,
        "avg_sharpe": round(avg_sharpe,  4),
        "max_dd":     round(max((r.get("max_dd",0) for r in ok), default=0.0), 4),
        "win_rate":   round(sum(r.get("win_rate",0) for r in ok) / len(ok) if ok else 0.0, 4),
        "profit_factor": round(sum(r.get("profit_factor",0) for r in ok) / len(ok) if ok else 0.0, 4),
        "fitness_score": round(avg_fitness, 4),
        "sharpe":        round(avg_sharpe, 4),
    }


def _run_parameter_sweep(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: grid-search over param_grid, return sorted results."""
    param_grid = payload.get("param_grid") or {}
    base_genome= payload.get("genome") or {}
    periods    = int(payload.get("periods", 260))
    symbol     = payload.get("symbol", "SYNTH")

    # Expand param_grid into flat list of param combos
    combos = _expand_grid(param_grid)
    if not combos:
        combos = [{}]

    sweep_results = []
    for combo in combos[:500]:   # cap to 500 combos per job
        genome = {**base_genome, "parameters": {**base_genome.get("parameters", {}), **combo}}
        r = _run_genome_backtest({"genome": genome, "symbol": symbol, "periods": periods})
        r["params"] = combo
        sweep_results.append(r)

    sweep_results.sort(key=lambda x: x.get("fitness_score", -99), reverse=True)
    best = sweep_results[0] if sweep_results else {}

    return {
        "genome_id":      base_genome.get("genome_id", ""),
        "symbol":         symbol,
        "n_combos":       len(sweep_results),
        "best_params":    best.get("params", {}),
        "best_sharpe":    best.get("sharpe", 0.0),
        "best_fitness":   best.get("fitness_score", -1.0),
        "sharpe":         best.get("sharpe", 0.0),
        "max_dd":         best.get("max_dd", 0.0),
        "win_rate":       best.get("win_rate", 0.0),
        "profit_factor":  best.get("profit_factor", 0.0),
        "fitness_score":  best.get("fitness_score", -1.0),
        "all_results":    sweep_results[:50],   # top-50 only
    }


def _run_walk_forward_batch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: walk-forward test a single genome."""
    genome   = payload.get("genome", {})
    candles  = payload.get("candles") or []
    periods  = int(payload.get("periods", 500))
    n_splits = int(payload.get("n_splits", 5))
    train_f  = float(payload.get("train_frac", 0.7))
    symbol   = payload.get("symbol", "SYNTH")

    try:
        from quant_ecosystem.research.backtest.backtest_engine import BacktestEngine  # noqa: lazy
        engine   = BacktestEngine()
        data     = candles if candles else periods
        strategy = _genome_to_callable(genome)
        wf       = engine.walk_forward(strategy, data, n_splits=n_splits, train_frac=train_f, symbol=symbol)
        summary  = wf.get("summary", {})
        oos      = wf.get("oos_metrics", {})
        return {
            "genome_id":     genome.get("genome_id", ""),
            "symbol":        symbol,
            "n_windows":     summary.get("n_windows",       0),
            "avg_sharpe":    summary.get("avg_sharpe",       0.0),
            "avg_max_dd":    summary.get("avg_max_dd",       0.0),
            "pct_profitable":summary.get("pct_profitable",   0.0),
            "oos_sharpe":    oos.get("sharpe",               0.0),
            "oos_max_dd":    oos.get("max_dd",               0.0),
            "total_oos_trades": summary.get("total_oos_trades", 0),
            "sharpe":        summary.get("avg_sharpe",       0.0),
            "max_dd":        summary.get("avg_max_dd",       0.0),
            "win_rate":      oos.get("win_rate",             0.0),
            "profit_factor": oos.get("profit_factor",        0.0),
            "fitness_score": _fitness(oos),
            "windows":       wf.get("windows", []),
        }
    except Exception as exc:
        return {"error": str(exc), "genome_id": genome.get("genome_id",""), "sharpe": 0.0, "fitness_score": -1.0}


def _run_monte_carlo(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: run N randomised backtests and return distribution stats."""
    import random as _rnd
    import math as _m

    genome    = payload.get("genome", {})
    n_runs    = int(payload.get("n_runs", 100))
    periods   = int(payload.get("periods", 260))
    symbol    = payload.get("symbol", "SYNTH")
    seed_base = int(payload.get("seed", 42))

    sharpes, dds, wrs, pfs = [], [], [], []

    try:
        from quant_ecosystem.research.backtest.backtest_engine import BacktestEngine  # noqa: lazy

        for i in range(min(n_runs, 500)):
            engine   = BacktestEngine()
            strategy = _genome_to_callable(genome)
            # Each run uses a freshly generated synthetic series (different seed via rng)
            _rnd.seed(seed_base + i)
            data = periods + _rnd.randint(-20, 20)   # slight length jitter
            r    = engine.run(strategy, max(60, data), symbol=symbol)
            m    = r.metrics
            sharpes.append(m.get("sharpe",         0.0))
            dds.append    (m.get("max_dd",          0.0))
            wrs.append    (m.get("win_rate",        0.0))
            pfs.append    (m.get("profit_factor",   0.0))

        def _pct(arr, p): return sorted(arr)[int(len(arr)*p/100)] if arr else 0.0
        def _mean(arr):   return sum(arr) / len(arr) if arr else 0.0
        def _std(arr):
            if len(arr) < 2: return 0.0
            m = _mean(arr)
            return _m.sqrt(sum((x-m)**2 for x in arr) / (len(arr)-1))

        avg_sharpe = _mean(sharpes)
        return {
            "genome_id":     genome.get("genome_id", ""),
            "symbol":        symbol,
            "n_runs":        n_runs,
            "sharpe_mean":   round(avg_sharpe,         4),
            "sharpe_std":    round(_std(sharpes),      4),
            "sharpe_p5":     round(_pct(sharpes, 5),   4),
            "sharpe_p50":    round(_pct(sharpes, 50),  4),
            "sharpe_p95":    round(_pct(sharpes, 95),  4),
            "max_dd_mean":   round(_mean(dds),         4),
            "max_dd_p95":    round(_pct(dds, 95),      4),
            "win_rate_mean": round(_mean(wrs),         4),
            "pf_mean":       round(_mean(pfs),         4),
            "pct_profitable":round(sum(1 for s in sharpes if s>0) / len(sharpes)*100, 2) if sharpes else 0.0,
            "sharpe":        round(avg_sharpe,         4),
            "max_dd":        round(_mean(dds),         4),
            "win_rate":      round(_mean(wrs),         4),
            "profit_factor": round(_mean(pfs),         4),
            "fitness_score": round(_fitness({"sharpe": avg_sharpe, "max_dd": _mean(dds), "win_rate": _mean(wrs), "profit_factor": _mean(pfs)}), 4),
        }
    except Exception as exc:
        return {"error": str(exc), "genome_id": genome.get("genome_id",""), "sharpe": 0.0, "fitness_score": -1.0}


def _run_factor_backtest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: build a factor signal and backtest it."""
    factor_name  = str(payload.get("factor_name", "momentum"))
    factor_params= payload.get("factor_params") or {}
    periods      = int(payload.get("periods", 260))
    symbol       = payload.get("symbol", "SYNTH")
    threshold    = float(payload.get("threshold", 0.0))

    try:
        from quant_ecosystem.research.factor_library_engine import FactorLibraryEngine  # noqa: lazy
        from quant_ecosystem.research.backtest.backtest_engine import BacktestEngine      # noqa: lazy

        flib  = FactorLibraryEngine()
        engine= BacktestEngine()

        def _factor_strategy(window: Dict) -> str:
            closes = list(window.get("close", []))
            if len(closes) < 30:
                return "HOLD"
            try:
                fn     = getattr(flib, factor_name, None)
                window_p = int(factor_params.get("window", 20))
                if fn is None:
                    return "HOLD"
                signal_val = fn(closes, window=window_p)
                # scalar or array?
                val = float(signal_val[-1]) if hasattr(signal_val, "__len__") and len(signal_val) else float(signal_val) if signal_val is not None else 0.0
                if val >  threshold: return "BUY"
                if val < -threshold: return "SELL"
            except Exception:
                pass
            return "HOLD"

        result = engine.run(_factor_strategy, periods, symbol=symbol)
        m = result.metrics
        return {
            "factor_name":   factor_name,
            "factor_params": factor_params,
            "symbol":        symbol,
            "sharpe":        m.get("sharpe",         0.0),
            "max_dd":        m.get("max_dd",          0.0),
            "win_rate":      m.get("win_rate",        0.0),
            "profit_factor": m.get("profit_factor",   0.0),
            "total_trades":  m.get("total_trades",    0),
            "fitness_score": _fitness(m),
        }
    except Exception as exc:
        return {"error": str(exc), "factor_name": factor_name, "sharpe": 0.0, "fitness_score": -1.0}


def _run_cross_validation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker: k-fold cross-validation on a strategy."""
    genome   = payload.get("genome", {})
    candles  = payload.get("candles") or []
    periods  = int(payload.get("periods", 500))
    k_folds  = int(payload.get("k_folds", 5))
    symbol   = payload.get("symbol", "SYNTH")

    try:
        from quant_ecosystem.research.backtest.backtest_engine import BacktestEngine  # noqa: lazy
        engine   = BacktestEngine()
        data     = candles if candles else engine._generate_candles(periods)
        strategy = _genome_to_callable(genome)
        n        = len(data)
        fold_size= n // k_folds
        fold_results = []

        for k in range(k_folds):
            test_start = k * fold_size
            test_end   = test_start + fold_size
            test_data  = data[test_start:test_end]
            if len(test_data) < 30:
                continue
            r = engine.run(strategy, test_data, symbol=symbol)
            m = r.metrics
            fold_results.append({"fold": k+1, "sharpe": m.get("sharpe",0.0), "max_dd": m.get("max_dd",0.0), "win_rate": m.get("win_rate",0.0), "profit_factor": m.get("profit_factor",0.0), "trades": m.get("total_trades",0)})

        if not fold_results:
            return {"error": "no_folds", "genome_id": genome.get("genome_id",""), "fitness_score": -1.0}

        avg_sharpe = sum(r["sharpe"] for r in fold_results) / len(fold_results)
        avg_dd     = sum(r["max_dd"] for r in fold_results) / len(fold_results)
        return {
            "genome_id":     genome.get("genome_id", ""),
            "symbol":        symbol,
            "k_folds":       k_folds,
            "fold_results":  fold_results,
            "avg_sharpe":    round(avg_sharpe, 4),
            "avg_max_dd":    round(avg_dd,     4),
            "sharpe":        round(avg_sharpe, 4),
            "max_dd":        round(avg_dd,     4),
            "win_rate":      round(sum(r["win_rate"] for r in fold_results) / len(fold_results), 4),
            "profit_factor": round(sum(r["profit_factor"] for r in fold_results) / len(fold_results), 4),
            "fitness_score": round(_fitness({"sharpe": avg_sharpe, "max_dd": avg_dd}), 4),
            "consistency":   round(sum(1 for r in fold_results if r["sharpe"] > 0) / len(fold_results), 4),
        }
    except Exception as exc:
        return {"error": str(exc), "genome_id": genome.get("genome_id",""), "fitness_score": -1.0}


# ---------------------------------------------------------------------------
# Worker-process dispatcher  (module-level so pickleable)
# ---------------------------------------------------------------------------

_JOB_FN_MAP: Dict[str, Callable] = {
    JobType.GENOME_BACKTEST:    _run_genome_backtest,
    JobType.GENOME_SWEEP:       _run_genome_sweep,
    JobType.PARAMETER_SWEEP:    _run_parameter_sweep,
    JobType.WALK_FORWARD_BATCH: _run_walk_forward_batch,
    JobType.MONTE_CARLO:        _run_monte_carlo,
    JobType.FACTOR_BACKTEST:    _run_factor_backtest,
    JobType.CROSS_VALIDATION:   _run_cross_validation,
}


def _dispatch_job(job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level function executed in a worker process."""
    fn = _JOB_FN_MAP.get(job_type)
    if fn is None:
        return {"error": f"unknown_job_type:{job_type}", "fitness_score": -1.0}
    return fn(payload)


# ---------------------------------------------------------------------------
# Utility helpers (also module-level so usable inside worker processes)
# ---------------------------------------------------------------------------

def _fitness(m: Dict) -> float:
    """Composite fitness from metrics dict."""
    s  = float(m.get("sharpe",         0.0))
    dd = float(m.get("max_dd",         0.0))
    wr = float(m.get("win_rate",       0.0))
    pf = float(m.get("profit_factor",  0.0))
    return max(-2.0, min(2.0,
        s * 0.40 +
        (wr / 100.0 - 0.5) * 2.0 * 0.20 +
        (pf - 1.0) * 0.25 -
        dd * 0.005
    ))


def _genome_to_callable(genome: Dict) -> Callable:
    """Build a strategy callable from a genome dict."""
    signal_gene = genome.get("signal_gene", {}) or {}
    indicator   = str(signal_gene.get("indicator", "momentum")).lower()
    threshold   = float(signal_gene.get("threshold", 0.0))
    period      = int(signal_gene.get("lookback", signal_gene.get("period", 20)))
    period      = max(5, min(period, 200))

    def _strategy(window: Dict) -> str:
        closes = window.get("close", [])
        if hasattr(closes, "tolist"):
            closes = closes.tolist()
        n = len(closes)
        if n < period + 2:
            return "HOLD"
        try:
            c = [float(x) for x in closes]
            if indicator == "momentum":
                sig = (c[-1] - c[-period]) / max(abs(c[-period]), 1e-9)
                return "BUY" if sig > threshold else ("SELL" if sig < -threshold else "HOLD")
            elif indicator == "rsi":
                gains = [max(c[i]-c[i-1], 0) for i in range(len(c)-period, len(c))]
                losses= [max(c[i-1]-c[i], 0) for i in range(len(c)-period, len(c))]
                ag, al= sum(gains)/period, sum(losses)/period
                rs = ag/al if al > 0 else 100.0
                rsi= 100 - 100/(1+rs)
                thr= float(threshold) if threshold > 1 else 50.0
                return "BUY" if rsi < thr else ("SELL" if rsi > (100-thr) else "HOLD")
            elif indicator in ("ma_cross", "ema_cross"):
                slow = int(signal_gene.get("slow_period", min(period*2, n-2)))
                slow = max(period+1, min(slow, n-2))
                fast_ma = sum(c[-period:]) / period
                slow_ma = sum(c[-slow:])   / slow
                prev_fast = sum(c[-period-1:-1]) / period
                prev_slow = sum(c[-slow-1:-1])   / slow
                if prev_fast <= prev_slow and fast_ma > slow_ma: return "BUY"
                if prev_fast >= prev_slow and fast_ma < slow_ma: return "SELL"
                return "HOLD"
            elif indicator == "breakout":
                high = max(c[-period-1:-1])
                low  = min(c[-period-1:-1])
                last = c[-1]
                if last > high * (1 + max(threshold, 0.001)): return "BUY"
                if last < low  * (1 - max(threshold, 0.001)): return "SELL"
                return "HOLD"
            elif indicator == "mean_reversion":
                ma   = sum(c[-period:]) / period
                std_ = (sum((x-ma)**2 for x in c[-period:]) / period) ** 0.5
                z    = (c[-1] - ma) / (std_ + 1e-9)
                thr  = float(threshold) if threshold > 0.01 else 1.5
                return "SELL" if z > thr else ("BUY" if z < -thr else "HOLD")
            elif indicator == "volatility_breakout":
                import math
                atr = sum(abs(c[i]-c[i-1]) for i in range(-period, 0)) / period
                if c[-1] > c[-2] + atr * max(float(threshold), 0.5): return "BUY"
                if c[-1] < c[-2] - atr * max(float(threshold), 0.5): return "SELL"
                return "HOLD"
        except Exception:
            pass
        return "HOLD"

    return _strategy


def _expand_grid(param_grid: Dict[str, List]) -> List[Dict]:
    """Expand {param: [v1,v2,...]} into list of flat combo dicts."""
    if not param_grid:
        return [{}]
    keys   = list(param_grid.keys())
    values = [list(v) if isinstance(v, (list, tuple)) else [v] for v in param_grid.values()]
    combos: List[Dict] = [{}]
    for k, vals in zip(keys, values):
        new_combos = []
        for combo in combos:
            for v in vals:
                new_combos.append({**combo, k: v})
        combos = new_combos
    return combos


# ---------------------------------------------------------------------------
# ResultStore
# ---------------------------------------------------------------------------

class ResultStore:
    """Thread-safe ring-buffer result store with built-in ranking."""

    def __init__(self, max_results: int = 50_000) -> None:
        self._lock          = threading.Lock()
        self._buf: deque    = deque(maxlen=max_results)
        self._by_id: Dict[str, GridResult] = {}
        self.total_ok       = 0
        self.total_failed   = 0
        self._promoted: List[GridResult] = []

    def accept(self, result: GridResult) -> None:
        with self._lock:
            self._buf.append(result)
            self._by_id[result.job_id] = result
            if result.ok:
                self.total_ok += 1
            else:
                self.total_failed += 1

    def get(self, job_id: str) -> Optional[GridResult]:
        with self._lock:
            r = self._by_id.get(job_id)
            return r

    def latest(self, n: int = 100) -> List[GridResult]:
        with self._lock:
            return list(self._buf)[-n:]

    def top_n(self, n: int = 20, key: str = "fitness") -> List[GridResult]:
        """Return top-n results by *key* (``"fitness"``, ``"sharpe"``, ``"win_rate"``)."""
        attr_map = {
            "fitness":  "fitness",
            "sharpe":   "sharpe",
            "win_rate": "win_rate",
            "pf":       "profit_factor",
        }
        attr = attr_map.get(key, "fitness")
        with self._lock:
            ok_results = [r for r in self._buf if r.ok]
        ok_results.sort(key=lambda r: getattr(r, attr, 0.0), reverse=True)
        return ok_results[:n]

    def promote(self, result: GridResult) -> None:
        with self._lock:
            self._promoted.append(result)

    def promoted(self) -> List[GridResult]:
        with self._lock:
            return list(self._promoted)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_ok":       self.total_ok,
                "total_failed":   self.total_failed,
                "buffered":       len(self._buf),
                "promoted":       len(self._promoted),
                "total_indexed":  len(self._by_id),
            }


# ---------------------------------------------------------------------------
# ParallelWorkerPool
# ---------------------------------------------------------------------------

class ParallelWorkerPool:
    """Manages a ``ProcessPoolExecutor`` for CPU-bound research jobs.

    Falls back to ``ThreadPoolExecutor`` when process spawning is unsafe
    (e.g. in pytest, Jupyter, or environments that disallow forking).
    """

    _USE_PROCESS_POOL = True  # can be overridden in tests

    def __init__(self, n_workers: int = 0) -> None:
        cpu_count = os.cpu_count() or 2
        self.n_workers = n_workers if n_workers > 0 else max(1, cpu_count - 1)
        self._pool: Optional[Any]  = None
        self._pool_type: str       = "none"
        self._lock                 = threading.Lock()
        self._active_futures: Dict[str, Future] = {}

    def start(self) -> None:
        if self._pool is not None:
            return
        with self._lock:
            if self._pool is not None:
                return
            if self._USE_PROCESS_POOL:
                try:
                    import multiprocessing as _mp   # noqa: lazy
                    ctx = _mp.get_context("spawn")
                    self._pool      = ProcessPoolExecutor(
                        max_workers   = self.n_workers,
                        mp_context    = ctx,
                    )
                    self._pool_type = "process"
                    logger.info(
                        "ParallelWorkerPool: ProcessPool started (%d workers)", self.n_workers
                    )
                    return
                except Exception as exc:
                    logger.warning("ParallelWorkerPool: ProcessPool unavailable (%s) — falling back to ThreadPool", exc)

            self._pool      = ThreadPoolExecutor(max_workers=self.n_workers)
            self._pool_type = "thread"
            logger.info(
                "ParallelWorkerPool: ThreadPool started (%d workers)", self.n_workers
            )

    def submit(
        self,
        job: GridJob,
        callback: Optional[Callable[[GridResult], None]] = None,
    ) -> Optional[Future]:
        """Submit a job to the pool; returns its Future."""
        if self._pool is None:
            self.start()
        if self._pool is None:
            return None

        t0 = time.time()

        def _done(fut: Future) -> None:
            elapsed = time.time() - t0
            try:
                raw = fut.result(timeout=job.timeout_sec)
            except Exception as exc:
                raw = {"error": str(exc), "fitness_score": -1.0}

            err = raw.get("error") if isinstance(raw, dict) else str(raw)
            ok  = err is None
            result = GridResult(
                job_id      = job.job_id,
                job_type    = job.job_type,
                ok          = ok,
                payload     = {"genome_id": job.payload.get("genome_id", job.payload.get("genome", {}).get("genome_id", ""))},
                result      = raw if isinstance(raw, dict) else {},
                error       = err if not ok else None,
                elapsed_sec = round(elapsed, 3),
                worker_pid  = os.getpid(),
            )
            with self._lock:
                self._active_futures.pop(job.job_id, None)
            if callback:
                try:
                    callback(result)
                except Exception as cb_exc:
                    logger.debug("ParallelWorkerPool: callback error: %s", cb_exc)

        try:
            fut = self._pool.submit(_dispatch_job, job.job_type, job.payload)
            fut.add_done_callback(_done)
            with self._lock:
                self._active_futures[job.job_id] = fut
            return fut
        except Exception as exc:
            logger.warning("ParallelWorkerPool.submit(%s): %s", job.job_id, exc)
            return None

    def active_count(self) -> int:
        with self._lock:
            return len(self._active_futures)

    def shutdown(self, wait: bool = True) -> None:
        if self._pool:
            self._pool.shutdown(wait=wait)
            self._pool = None
        logger.info("ParallelWorkerPool: shutdown complete")

    @property
    def pool_type(self) -> str:
        return self._pool_type


# ---------------------------------------------------------------------------
# GridScheduler
# ---------------------------------------------------------------------------

class GridScheduler:
    """Priority queue + rate-limiter that feeds the worker pool."""

    def __init__(
        self,
        pool: ParallelWorkerPool,
        result_store: ResultStore,
        max_in_flight: int = 0,
        poll_interval:  float = 0.05,
    ) -> None:
        self._pool            = pool
        self._store           = result_store
        self._queue: PriorityQueue = PriorityQueue(maxsize=100_000)
        self._max_in_flight   = max_in_flight or max(pool.n_workers * 4, 32)
        self._poll_interval   = poll_interval
        self._running         = False
        self._thread: Optional[threading.Thread] = None
        self._lock            = threading.Lock()
        self._callbacks: Dict[str, Callable] = {}
        self._submitted       = 0
        self._completed       = 0

    def enqueue(
        self,
        job: GridJob,
        callback: Optional[Callable[[GridResult], None]] = None,
    ) -> str:
        with self._lock:
            if callback:
                self._callbacks[job.job_id] = callback
        self._queue.put(job)
        return job.job_id

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._pool.start()
        self._thread = threading.Thread(
            target=self._dispatch_loop,
            daemon=True,
            name="GridScheduler",
        )
        self._thread.start()
        logger.info("GridScheduler started (max_in_flight=%d)", self._max_in_flight)

    def stop(self) -> None:
        self._running = False

    def _dispatch_loop(self) -> None:
        while self._running:
            in_flight = self._pool.active_count()
            if in_flight >= self._max_in_flight:
                time.sleep(self._poll_interval)
                continue
            try:
                job: GridJob = self._queue.get(timeout=self._poll_interval)
            except Empty:
                continue

            cb = self._callbacks.get(job.job_id)

            def _cb(result: GridResult, _cb=cb) -> None:
                self._store.accept(result)
                with self._lock:
                    self._completed += 1
                    self._callbacks.pop(result.job_id, None)
                if _cb:
                    try:
                        _cb(result)
                    except Exception:
                        pass

            self._pool.submit(job, callback=_cb)
            with self._lock:
                self._submitted += 1

    def qsize(self) -> int:
        return self._queue.qsize()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "submitted":   self._submitted,
                "completed":   self._completed,
                "queued":      self.qsize(),
                "in_flight":   self._pool.active_count(),
                "pool_type":   self._pool.pool_type,
                "n_workers":   self._pool.n_workers,
                "max_in_flight": self._max_in_flight,
            }


# ---------------------------------------------------------------------------
# ResearchGrid — main public class
# ---------------------------------------------------------------------------

class ResearchGrid:
    """Production parallel research grid for strategy and genome evaluation.

    Provides a high-throughput, CPU-parallel execution layer for all
    research workloads:

    - Genome backtests across symbols (``submit_genome_sweep``)
    - Hyperparameter grid-search (``submit_parameter_sweep``)
    - Walk-forward validation batches (``submit_walk_forward_batch``)
    - Monte-Carlo robustness testing (``submit_monte_carlo``)
    - Factor signal backtesting (``submit_factor_backtest``)
    - k-Fold cross-validation (``submit_cross_validation``)

    Parameters
    ----------
    n_workers:
        Number of parallel workers.  Defaults to ``CPU_count - 1``.
    promote_threshold:
        Minimum fitness score for auto-promotion to the genome library.
    genome_library:
        :class:`GenomeLibrary` instance.  Promoted genomes are stored here.
    backtest_engine:
        :class:`BacktestEngine` instance (used for inline / sync mode).

    Example
    -------
    >>> grid = ResearchGrid(n_workers=4)
    >>> grid.start()
    >>> job_ids = grid.submit_genome_sweep(genomes, symbols=["NSE:INFY","NSE:TCS"])
    >>> time.sleep(30)
    >>> top = grid.top_results(20)
    >>> grid.auto_promote()
    """

    def __init__(
        self,
        n_workers:          int   = 0,
        promote_threshold:  float = 0.5,
        genome_library      = None,
        backtest_engine     = None,
        result_callback:    Optional[Callable[[GridResult], None]] = None,
    ) -> None:
        cpu = os.cpu_count() or 2
        self._n_workers         = n_workers if n_workers > 0 else max(1, cpu - 1)
        self.promote_threshold  = float(promote_threshold)
        self._genome_library    = genome_library
        self._backtest_engine   = backtest_engine
        self._result_callback   = result_callback

        self._pool      = ParallelWorkerPool(n_workers=self._n_workers)
        self._store     = ResultStore()
        self._scheduler = GridScheduler(pool=self._pool, result_store=self._store)
        self._started   = False

        logger.info(
            "ResearchGrid initialized (workers=%d, promote_thresh=%.2f)",
            self._n_workers, self.promote_threshold,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler and worker pool."""
        if self._started:
            return
        self._scheduler.start()
        self._started = True
        logger.info("ResearchGrid started")

    def stop(self, wait: bool = True) -> None:
        """Gracefully drain queue and shut down workers."""
        self._scheduler.stop()
        self._pool.shutdown(wait=wait)
        self._started = False
        logger.info("ResearchGrid stopped")

    # ------------------------------------------------------------------
    # Submission API
    # ------------------------------------------------------------------

    def submit_genome_backtest(
        self,
        genome:         Dict,
        symbol:         str  = "SYNTH",
        periods:        int  = 260,
        slippage_bps:   float = 5.0,
        commission:     float = 20.0,
        candles:        Optional[List] = None,
        priority:       int  = 50,
        callback:       Optional[Callable[[GridResult], None]] = None,
    ) -> str:
        """Submit a single genome backtest.  Returns job_id."""
        self._ensure_started()
        job = GridJob(
            priority = priority,
            job_type = JobType.GENOME_BACKTEST,
            payload  = {
                "genome":       genome,
                "genome_id":    genome.get("genome_id", ""),
                "symbol":       symbol,
                "periods":      periods,
                "slippage_bps": slippage_bps,
                "commission":   commission,
                "candles":      candles or [],
            },
        )
        return self._scheduler.enqueue(job, callback=self._wrap_cb(callback))

    def submit_genome_sweep(
        self,
        genomes:        Iterable[Dict],
        symbols:        Optional[List[str]] = None,
        periods:        int   = 260,
        slippage_bps:   float = 5.0,
        commission:     float = 20.0,
        priority:       int   = 50,
        callback:       Optional[Callable[[GridResult], None]] = None,
    ) -> List[str]:
        """Submit N genomes × M symbols as parallel GENOME_SWEEP jobs.

        Returns list of job_ids (one per genome).
        """
        self._ensure_started()
        syms = symbols or ["SYNTH"]
        ids: List[str] = []
        for genome in genomes:
            job = GridJob(
                priority = priority,
                job_type = JobType.GENOME_SWEEP,
                payload  = {
                    "genome":       genome,
                    "genome_id":    genome.get("genome_id", ""),
                    "symbols":      syms,
                    "periods":      periods,
                    "slippage_bps": slippage_bps,
                    "commission":   commission,
                },
            )
            ids.append(self._scheduler.enqueue(job, callback=self._wrap_cb(callback)))
        logger.info("ResearchGrid.submit_genome_sweep: %d genomes × %d symbols", len(ids), len(syms))
        return ids

    def submit_parameter_sweep(
        self,
        genome:         Dict,
        param_grid:     Dict[str, List],
        symbol:         str  = "SYNTH",
        periods:        int  = 260,
        priority:       int  = 40,
        callback:       Optional[Callable[[GridResult], None]] = None,
    ) -> str:
        """Submit a hyperparameter grid-search.  Returns job_id."""
        self._ensure_started()
        job = GridJob(
            priority = priority,
            job_type = JobType.PARAMETER_SWEEP,
            payload  = {
                "genome":      genome,
                "genome_id":   genome.get("genome_id", ""),
                "param_grid":  param_grid,
                "symbol":      symbol,
                "periods":     periods,
            },
        )
        n_combos = 1
        for v in param_grid.values():
            n_combos *= len(v) if isinstance(v, (list, tuple)) else 1
        logger.info("ResearchGrid.submit_parameter_sweep: %d combos for genome=%s", n_combos, genome.get("genome_id", ""))
        return self._scheduler.enqueue(job, callback=self._wrap_cb(callback))

    def submit_walk_forward_batch(
        self,
        genomes:    Iterable[Dict],
        n_splits:   int   = 5,
        train_frac: float = 0.7,
        periods:    int   = 500,
        symbols:    Optional[List[str]] = None,
        candles:    Optional[List] = None,
        priority:   int   = 30,
        callback:   Optional[Callable[[GridResult], None]] = None,
    ) -> List[str]:
        """Submit walk-forward tests for a batch of genomes.  Returns job_ids."""
        self._ensure_started()
        syms = symbols or ["SYNTH"]
        ids: List[str] = []
        for genome in genomes:
            for sym in syms:
                job = GridJob(
                    priority = priority,
                    job_type = JobType.WALK_FORWARD_BATCH,
                    payload  = {
                        "genome":     genome,
                        "genome_id":  genome.get("genome_id", ""),
                        "symbol":     sym,
                        "periods":    periods,
                        "n_splits":   n_splits,
                        "train_frac": train_frac,
                        "candles":    candles or [],
                    },
                )
                ids.append(self._scheduler.enqueue(job, callback=self._wrap_cb(callback)))
        logger.info("ResearchGrid.submit_walk_forward_batch: %d jobs", len(ids))
        return ids

    def submit_monte_carlo(
        self,
        genome:     Dict,
        n_runs:     int   = 200,
        periods:    int   = 260,
        symbol:     str   = "SYNTH",
        priority:   int   = 60,
        callback:   Optional[Callable[[GridResult], None]] = None,
    ) -> str:
        """Submit a Monte-Carlo robustness test.  Returns job_id."""
        self._ensure_started()
        job = GridJob(
            priority     = priority,
            job_type     = JobType.MONTE_CARLO,
            timeout_sec  = 300.0,
            payload      = {
                "genome":    genome,
                "genome_id": genome.get("genome_id", ""),
                "symbol":    symbol,
                "n_runs":    n_runs,
                "periods":   periods,
            },
        )
        return self._scheduler.enqueue(job, callback=self._wrap_cb(callback))

    def submit_factor_backtest(
        self,
        factor_name:   str,
        factor_params: Optional[Dict] = None,
        symbol:        str = "SYNTH",
        periods:       int = 260,
        threshold:     float = 0.0,
        priority:      int  = 55,
        callback:      Optional[Callable[[GridResult], None]] = None,
    ) -> str:
        """Submit a factor-signal backtest.  Returns job_id."""
        self._ensure_started()
        job = GridJob(
            priority = priority,
            job_type = JobType.FACTOR_BACKTEST,
            payload  = {
                "factor_name":   factor_name,
                "factor_params": factor_params or {},
                "symbol":        symbol,
                "periods":       periods,
                "threshold":     threshold,
            },
        )
        return self._scheduler.enqueue(job, callback=self._wrap_cb(callback))

    def submit_cross_validation(
        self,
        genome:     Dict,
        k_folds:    int  = 5,
        periods:    int  = 500,
        symbol:     str  = "SYNTH",
        candles:    Optional[List] = None,
        priority:   int  = 45,
        callback:   Optional[Callable[[GridResult], None]] = None,
    ) -> str:
        """Submit a k-fold cross-validation job.  Returns job_id."""
        self._ensure_started()
        job = GridJob(
            priority = priority,
            job_type = JobType.CROSS_VALIDATION,
            payload  = {
                "genome":    genome,
                "genome_id": genome.get("genome_id",""),
                "symbol":    symbol,
                "k_folds":   k_folds,
                "periods":   periods,
                "candles":   candles or [],
            },
        )
        return self._scheduler.enqueue(job, callback=self._wrap_cb(callback))

    # ------------------------------------------------------------------
    # Bulk research cycle
    # ------------------------------------------------------------------

    def run_research_cycle(
        self,
        genomes:      Iterable[Dict],
        symbols:      Optional[List[str]] = None,
        n_splits:     int   = 5,
        run_mc:       bool  = False,
        mc_runs:      int   = 100,
        periods:      int   = 260,
        slippage_bps: float = 5.0,
        commission:   float = 20.0,
        timeout_sec:  float = 120.0,
    ) -> Dict[str, Any]:
        """Run a full parallel research cycle and block until complete.

        Executes in order:
        1. GENOME_SWEEP (all genomes × all symbols)
        2. WALK_FORWARD for top-20 by fitness
        3. MONTE_CARLO (if enabled) for top-10

        Returns summary dict with promoted genomes.
        """
        self._ensure_started()
        genomes = list(genomes)
        syms    = symbols or ["SYNTH"]
        t0      = time.time()
        all_ids: List[str] = []

        # Stage 1 — genome sweep
        sweep_ids = self.submit_genome_sweep(
            genomes, symbols=syms, periods=periods,
            slippage_bps=slippage_bps, commission=commission, priority=50,
        )
        all_ids.extend(sweep_ids)

        # Wait for stage 1
        self._wait_for_jobs(sweep_ids, timeout_sec=timeout_sec)

        # Stage 2 — walk-forward on top-20
        top20 = self.top_results(20)
        top_genomes = []
        for r in top20:
            gid = r.result.get("genome_id", "")
            g = next((g for g in genomes if g.get("genome_id") == gid), None)
            if g:
                top_genomes.append(g)

        wf_ids: List[str] = []
        if top_genomes:
            wf_ids = self.submit_walk_forward_batch(
                top_genomes, n_splits=n_splits, periods=max(periods, 500),
                symbols=syms, priority=30,
            )
            all_ids.extend(wf_ids)
            self._wait_for_jobs(wf_ids, timeout_sec=timeout_sec)

        # Stage 3 — Monte Carlo on top-10 (optional)
        mc_ids: List[str] = []
        if run_mc and top_genomes:
            for g in top_genomes[:10]:
                mc_ids.append(self.submit_monte_carlo(g, n_runs=mc_runs, periods=periods, priority=60))
            all_ids.extend(mc_ids)
            self._wait_for_jobs(mc_ids, timeout_sec=timeout_sec * 2)

        # Auto-promote
        n_promoted = self.auto_promote()

        elapsed = round(time.time() - t0, 2)
        sched   = self._scheduler.stats()

        logger.info(
            "ResearchGrid.run_research_cycle: %d genomes | %d jobs | %d promoted | %.1fs",
            len(genomes), len(all_ids), n_promoted, elapsed,
        )
        return {
            "genomes_evaluated": len(genomes),
            "total_jobs":        len(all_ids),
            "n_promoted":        n_promoted,
            "elapsed_sec":       elapsed,
            "jobs_per_sec":      round(len(all_ids) / max(elapsed, 0.1), 1),
            "scheduler_stats":   sched,
            "store_stats":       self._store.stats(),
            "top_results":       [{"genome_id": r.result.get("genome_id",""), "fitness": r.fitness, "sharpe": r.sharpe} for r in self.top_results(5)],
        }

    # ------------------------------------------------------------------
    # Results API
    # ------------------------------------------------------------------

    def get_result(self, job_id: str) -> Optional[GridResult]:
        return self._store.get(job_id)

    def top_results(self, n: int = 20, key: str = "fitness") -> List[GridResult]:
        return self._store.top_n(n, key=key)

    def latest_results(self, n: int = 50) -> List[GridResult]:
        return self._store.latest(n)

    def auto_promote(
        self,
        threshold:  Optional[float] = None,
        top_n:      int = 0,
    ) -> int:
        """Promote qualifying results to the genome library.

        Parameters
        ----------
        threshold:
            Minimum fitness score.  Defaults to ``promote_threshold``.
        top_n:
            If > 0, promote only the top-n results regardless of threshold.

        Returns number of genomes promoted.
        """
        thr = threshold if threshold is not None else self.promote_threshold
        promoted = 0

        if top_n > 0:
            candidates = self.top_results(top_n)
        else:
            candidates = [r for r in self._store.latest(10_000) if r.fitness >= thr]

        for result in candidates:
            genome_id = result.result.get("genome_id", "")
            if not genome_id:
                continue
            if self._genome_library is not None:
                try:
                    genome_data = result.payload.copy()
                    genome_data.update({
                        "genome_id":    genome_id,
                        "fitness_score":result.fitness,
                        "sharpe":       result.sharpe,
                        "max_dd":       result.max_dd,
                        "win_rate":     result.win_rate,
                        "profit_factor":result.profit_factor,
                        "source":       "research_grid",
                        "job_type":     result.job_type,
                    })
                    self._genome_library.store_genome(genome_id, genome_data)
                except Exception as exc:
                    logger.debug("auto_promote: genome_library error: %s", exc)
            self._store.promote(result)
            promoted += 1

        if promoted:
            logger.info("ResearchGrid.auto_promote: promoted %d genomes (threshold=%.2f)", promoted, thr)
        return promoted

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "started":     self._started,
            "scheduler":   self._scheduler.stats(),
            "store":       self._store.stats(),
            "pool_type":   self._pool.pool_type,
            "n_workers":   self._n_workers,
        }

    def __repr__(self) -> str:
        s = self._scheduler.stats()
        return (
            f"ResearchGrid(workers={self._n_workers}, "
            f"queued={s.get('queued',0)}, "
            f"completed={s.get('completed',0)}, "
            f"promoted={self._store.stats().get('promoted',0)})"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_started(self) -> None:
        if not self._started:
            self.start()

    def _wrap_cb(
        self,
        user_cb: Optional[Callable[[GridResult], None]],
    ) -> Optional[Callable[[GridResult], None]]:
        """Wrap user callback with the global result callback."""
        global_cb = self._result_callback

        def _cb(result: GridResult) -> None:
            if global_cb:
                try:
                    global_cb(result)
                except Exception:
                    pass
            if user_cb:
                try:
                    user_cb(result)
                except Exception:
                    pass

        return _cb if (user_cb or global_cb) else None

    def _wait_for_jobs(
        self,
        job_ids: List[str],
        timeout_sec: float = 120.0,
        poll: float = 0.1,
    ) -> int:
        """Block until all *job_ids* are complete or *timeout_sec* elapses.

        Returns number of completed jobs.
        """
        deadline = time.time() + timeout_sec
        remaining = set(job_ids)
        while remaining and time.time() < deadline:
            done = set()
            for jid in list(remaining):
                r = self._store.get(jid)
                if r is not None:
                    done.add(jid)
            remaining -= done
            if remaining:
                time.sleep(poll)
        return len(job_ids) - len(remaining)
