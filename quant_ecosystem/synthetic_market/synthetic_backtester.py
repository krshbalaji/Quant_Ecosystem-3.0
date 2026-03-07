"""
quant_ecosystem/synthetic_market/synthetic_backtester.py
=========================================================
Synthetic Backtester — Quant Ecosystem 3.0

Runs strategies against synthetic market data and computes a composite
robustness score measuring consistency across market regimes.

Institutional robustness testing philosophy
--------------------------------------------
A strategy that performs well only in one regime is a coin-flip in live
trading.  A robust strategy must:
  1. Generate positive Sharpe in at least 3 of 5 regimes.
  2. Not blow up (max_dd < threshold) in any single regime.
  3. Show consistent win rate across regimes (low coefficient of variation).
  4. Survive the stress event suite (flash crash + liquidity drop + gaps).
  5. Be walk-forward consistent (in-sample vs out-of-sample Sharpe ratio ≥ 0.7).

Robustness Score (0–100)
------------------------
  score = 100 × (
      0.30 × sharpe_consistency_score
    + 0.25 × regime_coverage_score
    + 0.20 × drawdown_resilience_score
    + 0.15 × stress_survival_score
    + 0.10 × walk_forward_consistency_score
  )

Integration
-----------
  • StrategyLab: SyntheticBacktester can be passed as strategy_lab=
    to GenomeEvaluator, providing evaluate_genome() hook.

  • GenomeEvaluator: GenomeEvaluator._backtest_score() already calls
    strategy_lab.evaluate_genome(genome) if available.  SyntheticBacktester
    implements that exact interface.

  • ResearchMemoryLayer: RobustnessResult is archived via
    PerformanceArchive (one slice per regime) and AlphaMemoryStore.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from quant_ecosystem.synthetic_market.synthetic_market_engine import (
    SyntheticMarketEngine,
    SyntheticSeries,
)
from quant_ecosystem.synthetic_market.regime_generator import Regime, RegimeGenerator
from quant_ecosystem.synthetic_market.shock_events import ShockEventInjector


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------

@dataclass
class RegimeResult:
    """Backtest metrics for one strategy in one regime."""
    regime:        str
    n_bars:        int
    sharpe:        float
    drawdown:      float      # max drawdown (positive value, e.g. 7.2 = 7.2%)
    profit_factor: float
    win_rate:      float
    total_return:  float
    trade_count:   int
    passed:        bool       # True if meets minimum quality thresholds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime":        self.regime,
            "n_bars":        self.n_bars,
            "sharpe":        self.sharpe,
            "drawdown":      self.drawdown,
            "profit_factor": self.profit_factor,
            "win_rate":      self.win_rate,
            "total_return":  self.total_return,
            "trade_count":   self.trade_count,
            "passed":        self.passed,
        }


@dataclass
class RobustnessResult:
    """
    Full robustness assessment of one strategy.

    regime_results       Per-regime backtest metrics.
    robustness_score     Composite score 0–100.
    sharpe               Weighted-average Sharpe across regimes.
    drawdown             Worst-case drawdown across all regimes.
    profit_factor        Average profit factor across regimes.
    win_rate             Average win rate across regimes.
    trade_count          Total trades across all regimes.
    stress_survived      True if strategy survived the stress event suite.
    walk_forward_ratio   OOS/IS Sharpe ratio from walk-forward test.
    regime_breadth       Fraction of regimes with positive Sharpe.
    grade                Letter grade: A B C D F.
    notes                Human-readable robustness notes.
    """

    strategy_id:            str
    regime_results:         List[RegimeResult]    = field(default_factory=list)
    robustness_score:       float                 = 0.0
    sharpe:                 float                 = 0.0
    drawdown:               float                 = 0.0
    profit_factor:          float                 = 0.0
    win_rate:               float                 = 0.0
    trade_count:            int                   = 0
    stress_survived:        bool                  = False
    walk_forward_ratio:     float                 = 0.0
    regime_breadth:         float                 = 0.0
    grade:                  str                   = "F"
    notes:                  List[str]             = field(default_factory=list)
    metadata:               Dict[str, Any]        = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id":        self.strategy_id,
            "robustness_score":   round(self.robustness_score, 4),
            "sharpe":             round(self.sharpe,           4),
            "drawdown":           round(self.drawdown,         4),
            "profit_factor":      round(self.profit_factor,    4),
            "win_rate":           round(self.win_rate,         4),
            "trade_count":        self.trade_count,
            "stress_survived":    self.stress_survived,
            "walk_forward_ratio": round(self.walk_forward_ratio, 4),
            "regime_breadth":     round(self.regime_breadth,   4),
            "grade":              self.grade,
            "notes":              self.notes,
            "regime_results":     [r.to_dict() for r in self.regime_results],
            "metadata":           self.metadata,
        }

    # GenomeEvaluator-compatible keys
    def as_backtest_metrics(self) -> Dict[str, float]:
        return {
            "sharpe":        self.sharpe,
            "drawdown":      self.drawdown,
            "profit_factor": self.profit_factor,
            "win_rate":      self.win_rate,
            "trade_count":   self.trade_count,
            "fitness_score": self.robustness_score / 100.0,
        }


# ---------------------------------------------------------------------------
# SyntheticBacktester
# ---------------------------------------------------------------------------

_PASS_SHARPE       = 0.30    # minimum per-regime Sharpe to "pass"
_PASS_MAX_DD       = 30.0    # maximum drawdown % before regime "fails"
_WF_CONSISTENCY    = 0.70    # OOS/IS Sharpe ≥ this for walk-forward pass


class SyntheticBacktester:
    """
    Runs strategies against synthetic market data and computes robustness scores.

    Integration modes
    -----------------
    1. evaluate_genome(genome_dict)
       Called automatically by GenomeEvaluator._backtest_score() when
       strategy_lab=SyntheticBacktester() is passed to GenomeEvaluator.

    2. evaluate_strategy(strategy_fn, strategy_id, ...)
       Direct evaluation with a callable strategy.

    3. evaluate_batch(strategies, ...)
       Batch evaluation returning a sorted leaderboard.

    Usage
    -----
        backtester = SyntheticBacktester(
            research_memory = router.research_memory,
            bars_per_regime = 150,
            seed            = 42,
        )

        # With GenomeEvaluator
        evaluator = GenomeEvaluator(strategy_lab=backtester, ...)

        # Direct
        result = backtester.evaluate_strategy(
            strategy_fn = my_fn,
            strategy_id = "ema_trend_015",
        )
        print(result.robustness_score, result.grade)
    """

    def __init__(
        self,
        research_memory   = None,
        bars_per_regime:  int           = 150,
        run_stress:       bool          = True,
        run_walk_forward: bool          = True,
        initial_capital:  float         = 100_000.0,
        seed:             Optional[int] = None,
        config:           Optional[Dict] = None,
        **kwargs,
    ) -> None:
        if config and isinstance(config, dict):
            bars_per_regime  = config.get("SYNTH_BARS_PER_REGIME",   bars_per_regime)
            run_stress       = config.get("SYNTH_RUN_STRESS",         run_stress)
            run_walk_forward = config.get("SYNTH_RUN_WALK_FORWARD",   run_walk_forward)

        self._rm              = research_memory
        self._bars_per_regime = max(50, bars_per_regime)
        self._run_stress      = run_stress
        self._run_wf          = run_walk_forward
        self._capital         = initial_capital
        self._seed            = seed
        self._engine          = SyntheticMarketEngine(seed=seed)
        self._injector        = ShockEventInjector(seed=seed)

        # Lazy-loaded BacktestEngine from existing codebase
        self._bt_engine       = None

    def set_research_memory(self, rm) -> None:
        self._rm = rm

    # ------------------------------------------------------------------
    # GenomeEvaluator hook
    # ------------------------------------------------------------------

    def evaluate_genome(self, genome: Dict) -> Dict[str, float]:
        """
        Called by GenomeEvaluator._backtest_score() when strategy_lab is set.

        Converts a genome dict to a strategy callable using the same
        translation logic as StrategyLabController, runs the full
        robustness suite, and returns a normalised metrics dict.
        """
        strategy_fn = self._genome_to_callable(genome)
        gid         = str(genome.get("genome_id", f"genome_{int(time.time())}"))
        result      = self.evaluate_strategy(
            strategy_fn = strategy_fn,
            strategy_id = gid,
            regime      = None,     # sweep all regimes
            archive     = True,
        )
        return result.as_backtest_metrics()

    # ------------------------------------------------------------------
    # Primary evaluation API
    # ------------------------------------------------------------------

    def evaluate_strategy(
        self,
        strategy_fn:  Callable,
        strategy_id:  str          = "",
        regime:       Optional[str] = None,  # None = sweep all
        family:       str           = "unknown",
        archive:      bool          = True,
    ) -> RobustnessResult:
        """
        Full robustness evaluation of a strategy function.

        Parameters
        ----------
        strategy_fn     Callable: f(window_dict) → "BUY" | "SELL" | "HOLD"
        strategy_id     Identifier string for record-keeping.
        regime          If set, test against only this one regime.
                        If None, sweep all five regimes.
        archive         If True, write results to ResearchMemoryLayer.
        """
        sid = strategy_id or f"strat_{int(time.time())}"
        bt  = self._get_backtest_engine()

        # ── 1. Per-regime results ────────────────────────────────────
        if regime:
            regimes_to_run = [Regime(regime)]
        else:
            regimes_to_run = list(Regime)

        regime_results: List[RegimeResult] = []
        for reg in regimes_to_run:
            series = self._engine.generate_stress(
                regime        = reg,
                n_bars        = self._bars_per_regime,
                inject_shocks = False,
                seed          = self._seed,
            )
            rr = self._run_one_regime(bt, strategy_fn, series, reg.value)
            regime_results.append(rr)

        # ── 2. Stress event test ─────────────────────────────────────
        stress_survived = False
        if self._run_stress:
            stress_survived = self._run_stress_test(bt, strategy_fn)

        # ── 3. Walk-forward consistency ──────────────────────────────
        wf_ratio = 0.0
        if self._run_wf:
            wf_ratio = self._walk_forward_consistency(bt, strategy_fn)

        # ── 4. Composite robustness score ────────────────────────────
        result = self._score(
            sid, regime_results, stress_survived, wf_ratio, family
        )

        # ── 5. Archive to ResearchMemoryLayer ────────────────────────
        if archive and self._rm is not None:
            self._archive_result(result)

        return result

    def evaluate_batch(
        self,
        strategies: List[Dict],   # list of {"strategy_id": ..., "callable": ..., "family": ...}
        archive:    bool = True,
    ) -> List[RobustnessResult]:
        """
        Evaluate a batch of strategies and return sorted leaderboard.
        Each dict must have 'callable' key with a strategy function.
        """
        results = []
        for item in strategies:
            fn  = item.get("callable") or item.get("strategy_fn")
            if fn is None:
                continue
            sid    = str(item.get("strategy_id", f"strat_{int(time.time())}"))
            family = str(item.get("family", "unknown"))
            r = self.evaluate_strategy(fn, strategy_id=sid, family=family, archive=archive)
            results.append(r)
        results.sort(key=lambda r: r.robustness_score, reverse=True)
        return results

    def regime_leaderboard(
        self,
        strategies: List[Dict],
        regime:     str,
    ) -> List[RobustnessResult]:
        """Evaluate strategies and rank by performance in one specific regime."""
        results = self.evaluate_batch(strategies, archive=False)
        for r in results:
            # Re-sort by regime-specific Sharpe
            rr = next((x for x in r.regime_results if x.regime == regime), None)
            r.metadata["regime_sharpe"] = rr.sharpe if rr else 0.0
        results.sort(key=lambda r: r.metadata.get("regime_sharpe", 0.0), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Internal: single-regime backtest
    # ------------------------------------------------------------------

    def _run_one_regime(
        self,
        bt:          Any,
        strategy_fn: Callable,
        series:      SyntheticSeries,
        regime_name: str,
    ) -> RegimeResult:
        try:
            result  = bt.run(strategy_fn, series.candles, symbol=regime_name)
            metrics = result.metrics
        except Exception:
            metrics = {}

        sharpe     = float(metrics.get("sharpe",        0.0))
        drawdown   = float(metrics.get("max_dd",        0.0))
        pf         = float(metrics.get("profit_factor", 0.0))
        wr         = float(metrics.get("win_rate",      0.0))
        total_ret  = float(metrics.get("total_return_pct", 0.0))
        trades     = int(metrics.get("total_trades",   0))

        passed = (
            sharpe   >= _PASS_SHARPE  and
            drawdown <= _PASS_MAX_DD
        )
        return RegimeResult(
            regime        = regime_name,
            n_bars        = series.n_bars,
            sharpe        = round(sharpe,   4),
            drawdown      = round(drawdown, 4),
            profit_factor = round(pf,       4),
            win_rate      = round(wr,       4),
            total_return  = round(total_ret, 4),
            trade_count   = trades,
            passed        = passed,
        )

    def _run_stress_test(self, bt: Any, strategy_fn: Callable) -> bool:
        """Returns True if strategy survives the stress event suite."""
        try:
            series = self._engine.generate(
                n_bars        = 252,
                inject_shocks = False,
                seed          = self._seed,
            )
            candles, _ = self._injector.inject_stress_suite(series.candles)
            result     = bt.run(strategy_fn, candles, symbol="STRESS")
            metrics    = result.metrics
            return (
                float(metrics.get("sharpe",  0.0)) > -0.5
                and float(metrics.get("max_dd", 100.0)) < 45.0
            )
        except Exception:
            return False

    def _walk_forward_consistency(self, bt: Any, strategy_fn: Callable) -> float:
        """
        Walk-forward ratio: OOS Sharpe / IS Sharpe.
        Values ≥ 0.7 indicate good generalisation.
        """
        try:
            series = self._engine.generate(n_bars=504, seed=self._seed)
            wf     = bt.walk_forward(strategy_fn, series.candles, n_splits=4, train_frac=0.7)
            summary = wf.get("summary", {})
            oos_sharpe = float(wf.get("oos_metrics", {}).get("sharpe", 0.0))
            # Estimate IS Sharpe from first window's training performance
            is_sharpe  = float(summary.get("avg_sharpe", oos_sharpe))
            if abs(is_sharpe) < 0.01:
                return 1.0    # neither measured — neutral
            return round(oos_sharpe / is_sharpe, 4) if is_sharpe > 0 else 0.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Robustness scoring
    # ------------------------------------------------------------------

    def _score(
        self,
        strategy_id:     str,
        regime_results:  List[RegimeResult],
        stress_survived: bool,
        wf_ratio:        float,
        family:          str,
    ) -> RobustnessResult:

        if not regime_results:
            return RobustnessResult(strategy_id=strategy_id, grade="F",
                                    notes=["No regime results"])

        sharpes    = [r.sharpe        for r in regime_results]
        drawdowns  = [r.drawdown      for r in regime_results]
        pfs        = [r.profit_factor for r in regime_results]
        win_rates  = [r.win_rate      for r in regime_results]
        trades     = [r.trade_count   for r in regime_results]
        passed     = [r.passed        for r in regime_results]
        n          = len(regime_results)

        avg_sharpe    = sum(sharpes)    / n
        worst_dd      = max(drawdowns,  default=0.0)
        avg_pf        = sum(pfs)        / n
        avg_wr        = sum(win_rates)  / n
        total_trades  = sum(trades)
        regime_breadth = sum(1 for s in sharpes if s > 0) / n

        # ── Component scores ────────────────────────────────────────────

        # 1. Sharpe consistency: penalise high CoV
        mean_s   = sum(sharpes) / n
        std_s    = math.sqrt(sum((s - mean_s)**2 for s in sharpes) / max(n-1, 1))
        cov      = std_s / abs(mean_s) if abs(mean_s) > 0.01 else 2.0
        sharpe_consistency = max(0.0, 1.0 - min(cov, 2.0) / 2.0)
        # Clip by absolute level
        sharpe_consistency *= min(1.0, max(0.0, avg_sharpe / 2.0))

        # 2. Regime coverage: fraction of regimes with positive Sharpe
        regime_coverage = regime_breadth

        # 3. Drawdown resilience: worst drawdown below threshold
        dd_score = max(0.0, 1.0 - worst_dd / _PASS_MAX_DD)
        dd_score = min(1.0, dd_score)

        # 4. Stress survival
        stress_score = 1.0 if stress_survived else 0.0

        # 5. Walk-forward consistency
        wf_score = min(1.0, max(0.0, wf_ratio))

        # ── Composite (weighted) ─────────────────────────────────────────
        composite = (
            0.30 * sharpe_consistency
          + 0.25 * regime_coverage
          + 0.20 * dd_score
          + 0.15 * stress_score
          + 0.10 * wf_score
        )
        robustness_score = round(composite * 100.0, 4)

        # ── Grade ────────────────────────────────────────────────────────
        if robustness_score >= 75:   grade = "A"
        elif robustness_score >= 60: grade = "B"
        elif robustness_score >= 45: grade = "C"
        elif robustness_score >= 30: grade = "D"
        else:                        grade = "F"

        # ── Narrative notes ──────────────────────────────────────────────
        notes = []
        if avg_sharpe < 0:
            notes.append("⚠ Negative average Sharpe — strategy loses money on average")
        if regime_breadth < 0.4:
            notes.append(f"⚠ Only profitable in {regime_breadth:.0%} of regimes — likely overfit")
        if worst_dd > 20.0:
            notes.append(f"⚠ Worst-case drawdown {worst_dd:.1f}% — consider position sizing")
        if not stress_survived:
            notes.append("⚠ Failed stress event suite — vulnerable to flash crashes or liquidity gaps")
        if wf_ratio < _WF_CONSISTENCY and wf_ratio > 0:
            notes.append(f"⚠ Walk-forward ratio {wf_ratio:.2f} < {_WF_CONSISTENCY} — possible in-sample overfit")
        if cov < 0.3 and avg_sharpe > 0.5:
            notes.append("✓ Highly consistent Sharpe across regimes")
        if regime_breadth >= 0.8:
            notes.append("✓ Profitable in most market regimes")
        if not notes:
            notes.append("Strategy passed all basic robustness checks")

        return RobustnessResult(
            strategy_id        = strategy_id,
            regime_results     = regime_results,
            robustness_score   = robustness_score,
            sharpe             = round(avg_sharpe,   4),
            drawdown           = round(worst_dd,     4),
            profit_factor      = round(avg_pf,       4),
            win_rate           = round(avg_wr,       4),
            trade_count        = total_trades,
            stress_survived    = stress_survived,
            walk_forward_ratio = round(wf_ratio, 4),
            regime_breadth     = round(regime_breadth, 4),
            grade              = grade,
            notes              = notes,
            metadata = {
                "family":            family,
                "sharpe_consistency": round(sharpe_consistency, 4),
                "regime_coverage":    round(regime_coverage,    4),
                "dd_score":           round(dd_score,           4),
                "stress_score":       stress_score,
                "wf_score":           round(wf_score,           4),
                "created_at":         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

    # ------------------------------------------------------------------
    # ResearchMemoryLayer archival
    # ------------------------------------------------------------------

    def _archive_result(self, result: RobustnessResult) -> None:
        """Write RobustnessResult into PerformanceArchive + AlphaMemoryStore."""
        if self._rm is None:
            return
        try:
            for rr in result.regime_results:
                self._rm.performance.add_slice_from_dict({
                    "strategy_id":   result.strategy_id,
                    "phase":         "backtest",
                    "regime":        rr.regime,
                    "sharpe":        rr.sharpe,
                    "drawdown":      -abs(rr.drawdown),
                    "profit_factor": rr.profit_factor,
                    "win_rate":      rr.win_rate,
                    "trade_count":   rr.trade_count,
                    "total_pnl":     rr.total_return,
                    "notes":         f"synthetic robustness test regime={rr.regime}",
                })

            # Update or create AlphaRecord
            existing = self._rm.alpha_store.get(result.strategy_id)
            if existing is not None:
                existing.sharpe        = result.sharpe
                existing.drawdown      = -abs(result.drawdown)
                existing.profit_factor = result.profit_factor
                existing.win_rate      = result.win_rate
                existing.trade_count   = result.trade_count
                existing.extra["robustness_score"] = result.robustness_score
                existing.extra["grade"]            = result.grade
                self._rm.alpha_store.record(existing)
            else:
                family = result.metadata.get("family", "unknown")
                self._rm.alpha_store.record_from_dict({
                    "strategy_id":   result.strategy_id,
                    "family":        family,
                    "regime":        "all",
                    "sharpe":        result.sharpe,
                    "drawdown":      -abs(result.drawdown),
                    "profit_factor": result.profit_factor,
                    "win_rate":      result.win_rate,
                    "trade_count":   result.trade_count,
                    "status":        "discovered",
                    "extra": {
                        "robustness_score": result.robustness_score,
                        "grade":            result.grade,
                    },
                    "tags": ["synthetic_backtest", f"grade_{result.grade}", family],
                })
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Genome → strategy callable
    # ------------------------------------------------------------------

    @staticmethod
    def _genome_to_callable(genome: Dict) -> Callable:
        """
        Convert a genome dict to a strategy callable.

        Uses the same translation logic as StrategyLabController._build_callable()
        so GenomeEvaluator gets consistent behaviour when strategy_lab is set.
        """
        signal    = dict(genome.get("signal_gene",    {}) or {})
        risk      = dict(genome.get("risk_gene",      {}) or {})
        entry_g   = dict(genome.get("entry_gene",     {}) or {})
        exit_g    = dict(genome.get("exit_gene",      {}) or {})

        sig_type   = str(signal.get("type",         "momentum")).lower()
        threshold  = float(signal.get("threshold",  0.60))
        ind1       = str(signal.get("indicator_1",  "EMA")).upper()
        fast_p     = max(5,  int(signal.get("fast_period",  10)))
        slow_p     = max(fast_p+1, int(signal.get("slow_period", 30)))
        rsi_p      = max(5,  int(signal.get("period",       14)))
        conf_bars  = max(1,  int(entry_g.get("confirmation_bars", 1)))
        tp_r       = float(exit_g.get("take_profit_r", 2.0))
        sl_r       = float(exit_g.get("stop_loss_r",   1.0))

        def strategy_fn(window: Dict) -> str:
            close = list(window.get("close", []))
            if len(close) < slow_p + conf_bars + 2:
                return "HOLD"

            fast_ema = sum(close[-fast_p:]) / fast_p
            slow_ema = sum(close[-slow_p:]) / slow_p
            mom      = close[-1] - close[-rsi_p]

            # RSI proxy
            gains  = [max(0, close[i] - close[i-1]) for i in range(-rsi_p, 0)]
            losses = [max(0, close[i-1] - close[i]) for i in range(-rsi_p, 0)]
            ag     = sum(gains)  / max(1, len(gains))
            al     = sum(losses) / max(1, len(losses))
            rs     = ag / al if al > 1e-9 else 10.0
            rsi    = 100.0 - 100.0 / (1.0 + rs)

            if sig_type in ("momentum", "breakout", "trend_following"):
                if fast_ema > slow_ema and mom > 0:
                    return "BUY"
                if fast_ema < slow_ema and mom < 0:
                    return "SELL"
            elif sig_type in ("mean_reversion", "stat_arb", "reversion"):
                if rsi < (1.0 - threshold) * 100:
                    return "BUY"
                if rsi > threshold * 100:
                    return "SELL"
            elif sig_type == "volatility":
                vol_proxy = abs(close[-1] - close[-rsi_p]) / max(close[-rsi_p], 1e-9)
                if vol_proxy > threshold * 0.1:
                    return "BUY" if fast_ema > slow_ema else "SELL"
            else:
                if fast_ema > slow_ema:
                    return "BUY"
                if fast_ema < slow_ema:
                    return "SELL"
            return "HOLD"

        return strategy_fn

    # ------------------------------------------------------------------
    # Lazy BacktestEngine loader
    # ------------------------------------------------------------------

    def _get_backtest_engine(self) -> Any:
        if self._bt_engine is not None:
            return self._bt_engine
        try:
            from quant_ecosystem.research.backtest.backtest_engine import (
                BacktestEngine,
                FixedBpsSlippage,
                FlatCommission,
            )
            self._bt_engine = BacktestEngine(
                slippage_model   = FixedBpsSlippage(bps=5.0),
                commission_model = FlatCommission(flat=20.0),
                initial_capital  = self._capital,
            )
        except Exception:
            # Minimal fallback if import fails
            self._bt_engine = _MinimalBacktestEngine(initial_capital=self._capital)
        return self._bt_engine


# ---------------------------------------------------------------------------
# Minimal fallback BacktestEngine (used only if import path fails)
# ---------------------------------------------------------------------------

class _MinimalBacktestEngine:
    """Thin fallback engine used only when the production BacktestEngine
    import path is unavailable (e.g. in isolated unit tests)."""

    def __init__(self, initial_capital: float = 100_000.0):
        self._capital = initial_capital

    def run(self, strategy_fn, candles, symbol="SYNTH"):
        closes   = [c["close"] for c in candles]
        position = 0
        entry    = 0.0
        equity   = self._capital
        curve    = [equity]
        trades_n = 0
        pnls     = []

        for i in range(20, len(closes)):
            window = {"close": closes[:i+1], "open": closes[:i+1],
                      "volume": [100000]*i, "candles": candles[:i+1], "index": i}
            try:
                sig = strategy_fn(window)
            except Exception:
                sig = "HOLD"

            if sig == "BUY"  and position == 0:
                position, entry = 1, closes[i]
            elif sig == "SELL" and position == 1:
                pnl   = (closes[i] - entry) / entry
                pnls.append(pnl)
                equity *= (1 + pnl)
                trades_n += 1
                position  = 0
            curve.append(equity)

        wins   = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        n      = max(len(pnls), 1)
        mean_r = sum(pnls) / n if pnls else 0.0
        std_r  = math.sqrt(sum((p - mean_r)**2 for p in pnls) / max(n-1, 1)) if len(pnls) > 1 else 1e-6
        sharpe = mean_r / std_r * math.sqrt(252) if std_r > 0 else 0.0
        pf     = abs(sum(wins)) / abs(sum(losses)) if losses else (abs(sum(wins)) if wins else 0.0)
        wr     = len(wins) / n * 100.0

        peak = curve[0]
        mdd  = 0.0
        for v in curve:
            peak = max(peak, v)
            if peak > 0: mdd = max(mdd, (peak - v) / peak * 100.0)

        return type("R", (), {"metrics": {
            "sharpe": round(sharpe, 4), "max_dd": round(mdd, 4),
            "profit_factor": round(pf, 4), "win_rate": round(wr, 4),
            "total_trades": trades_n, "total_return_pct": round((equity/self._capital-1)*100, 4),
            "returns": pnls,
        }})()

    def walk_forward(self, strategy_fn, candles, n_splits=4, train_frac=0.7):
        n = len(candles)
        if n < 60:
            return {"windows": [], "oos_metrics": {}, "summary": {"avg_sharpe": 0.0}}
        step = n // n_splits
        sharpes = []
        for i in range(n_splits):
            test = candles[i*step + int(step*train_frac): (i+1)*step]
            if len(test) < 10: continue
            r = self.run(strategy_fn, test)
            sharpes.append(r.metrics.get("sharpe", 0.0))
        avg = sum(sharpes) / len(sharpes) if sharpes else 0.0
        return {"oos_metrics": {"sharpe": avg}, "summary": {"avg_sharpe": avg}, "windows": []}
