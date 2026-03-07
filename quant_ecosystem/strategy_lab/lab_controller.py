"""Orchestration controller for the Self-Evolving Strategy Lab."""

from __future__ import annotations
from quant_ecosystem.alpha_discovery.alpha_discovery_engine import AlphaDiscoveryEngine
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.strategy_lab.backtest_engine import BacktestEngine
from quant_ecosystem.strategy_lab.mutation_pipeline import MutationPipeline
from quant_ecosystem.strategy_lab.strategy_generator import StrategyGenerator
from quant_ecosystem.strategy_lab.strategy_repository import StrategyRepository
from quant_ecosystem.strategy_lab.strategy_validator import StrategyValidator


class StrategyLabController:
    """Runs end-to-end strategy generation/mutation/backtest/validation pipeline.

    SyntheticBacktester integration
    --------------------------------
    Pass synthetic_backtester=SyntheticBacktester(...) to enable regime-aware
    robustness testing.  When set:
      • run_synthetic_backtests(strategies) returns RobustnessResult per strategy.
      • evaluate_genome(genome) is available as the GenomeEvaluator hook.
    """

    def __init__(
        self,
        strategy_bank_layer=None,
        mutation_layer=None,
        meta_strategy_brain=None,
        generator: Optional[StrategyGenerator] = None,
        mutation_pipeline: Optional[MutationPipeline] = None,
        backtest_engine: Optional[BacktestEngine] = None,
        validator: Optional[StrategyValidator] = None,
        repository: Optional[StrategyRepository] = None,
        synthetic_backtester=None,
        sandbox_mode: bool = True, **kwargs
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.mutation_layer = mutation_layer
        self.meta_strategy_brain = meta_strategy_brain
        self.generator = generator or StrategyGenerator()
        self.mutation_pipeline = mutation_pipeline or MutationPipeline(mutation_layer=mutation_layer)
        self.backtest_engine = backtest_engine or BacktestEngine()
        self.validator = validator or StrategyValidator()
        self.repository = repository or StrategyRepository()
        self.synthetic_backtester = synthetic_backtester
        self.sandbox_mode = bool(sandbox_mode)

    # ------------------------------------------------------------------
    # GenomeEvaluator hook: strategy_lab.evaluate_genome(genome) -> metrics
    # ------------------------------------------------------------------

    def evaluate_genome(self, genome: Dict) -> Dict:
        """Called by GenomeEvaluator._backtest_score() when strategy_lab= is this object.

        Routes to SyntheticBacktester when available (full regime-sweep robustness),
        otherwise falls back to a standard 260-bar backtest.
        """
        if self.synthetic_backtester is not None:
            return self.synthetic_backtester.evaluate_genome(genome)
        # Fallback: standard backtest
        gid    = str(genome.get("genome_id", "genome"))
        signal = dict(genome.get("signal_gene", {}) or {})
        strategy_dict = {
            "id":            gid,
            "strategy_type": str(signal.get("type", "momentum")).lower(),
            "parameters": {
                "ema_fast":   int(float(signal.get("fast_period",  10))),
                "ema_slow":   int(float(signal.get("slow_period",  30))),
                "rsi_length": int(float(signal.get("period",       14))),
            },
        }
        # run_batch wraps core_engine; we call run_strategy directly to avoid
        # the periods= kwarg difference between the wrapper and core engine
        try:
            result = self.backtest_engine.run_strategy(strategy_dict, periods=260)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Synthetic robustness testing
    # ------------------------------------------------------------------

    def run_synthetic_backtests(
        self,
        strategies: "Iterable[Dict]",
        archive:    bool = True,
    ) -> "List[Dict]":
        """
        Run regime-aware robustness evaluation on strategy dicts.

        Requires synthetic_backtester to be set.  If not set, returns an
        empty list without raising.

        Each returned dict is the original strategy dict enriched with:
            robustness_score    float  (0-100)
            grade               str    (A/B/C/D/F)
            synth_sharpe        float
            synth_drawdown      float
            synth_profit_factor float
            synth_win_rate      float
            synth_regime_breadth float
            synth_stress_survived bool
            synth_regime_results  list  (per-regime metrics)
        """
        if self.synthetic_backtester is None:
            return []

        results = []
        for strat in list(strategies):
            gid    = str(strat.get("id", strat.get("strategy_id", strat.get("genome_id", ""))))
            family = str(strat.get("family", strat.get("strategy_type", "unknown")))
            fn     = self._strategy_dict_to_callable(strat)
            r      = self.synthetic_backtester.evaluate_strategy(
                strategy_fn = fn,
                strategy_id = gid,
                family      = family,
                archive     = archive,
            )
            enriched = dict(strat)
            enriched.update({
                "robustness_score":      r.robustness_score,
                "grade":                 r.grade,
                "synth_sharpe":          r.sharpe,
                "synth_drawdown":        r.drawdown,
                "synth_profit_factor":   r.profit_factor,
                "synth_win_rate":        r.win_rate,
                "synth_regime_breadth":  r.regime_breadth,
                "synth_stress_survived": r.stress_survived,
                "synth_regime_results":  [rr.to_dict() for rr in r.regime_results],
                "synth_notes":           r.notes,
            })
            results.append(enriched)

        # Sort by robustness score descending
        results.sort(key=lambda x: x.get("robustness_score", 0.0), reverse=True)
        return results

    @staticmethod
    def _strategy_dict_to_callable(strategy: Dict):
        """Convert a strategy dict (StrategyLab format) to a signal callable."""
        params       = dict(strategy.get("parameters", {}) or {})
        sig_type     = str(strategy.get("strategy_type", strategy.get("family", "momentum"))).lower()
        ema_fast     = max(3,            int(float(params.get("ema_fast",   9))))
        ema_slow     = max(ema_fast + 1, int(float(params.get("ema_slow",  21))))
        rsi_length   = max(5,            int(float(params.get("rsi_length", 14))))

        def fn(window: Dict) -> str:
            close = list(window.get("close", []))
            if len(close) < max(ema_slow + 2, rsi_length + 2):
                return "HOLD"
            fast = sum(close[-ema_fast:]) / ema_fast
            slow = sum(close[-ema_slow:]) / ema_slow
            mom  = close[-1] - close[-rsi_length]
            gains  = [max(0, close[i] - close[i-1]) for i in range(-rsi_length, 0)]
            losses = [max(0, close[i-1] - close[i]) for i in range(-rsi_length, 0)]
            ag     = sum(gains)  / max(1, len(gains))
            al     = sum(losses) / max(1, len(losses))
            rsi    = 100.0 - 100.0 / (1.0 + ag / al) if al > 1e-9 else 50.0
            if sig_type in {"trend_following", "momentum", "breakout"}:
                if fast > slow and mom > 0: return "BUY"
                if fast < slow and mom < 0: return "SELL"
            elif sig_type in {"mean_reversion", "pairs_trading", "statistical_arbitrage"}:
                if rsi < 35: return "BUY"
                if rsi > 65: return "SELL"
            elif sig_type == "volatility":
                if abs(mom / max(close[-rsi_length], 1e-9)) > 0.02:
                    return "BUY" if fast > slow else "SELL"
            return "HOLD"

        return fn

    def run_strategy_generation(self, count: int = 50) -> List[Dict]:
        rows = self.generator.generate(count=count)
        self.repository.save_research(rows)
        return rows
        
        discovery = AlphaDiscoveryEngine()
        discovery.discover(50)
    
    def run_mutation_pipeline(self, base_strategies: Iterable[Dict], variants_per_base: int = 20) -> List[Dict]:
        mutated = self.mutation_pipeline.mutate(base_strategies, variants_per_base=variants_per_base)
        self.repository.save_research(mutated)
        return mutated

    def run_backtests(self, strategies: Iterable[Dict], periods: int = 260) -> List[Dict]:
        return self.backtest_engine.run_batch(strategies, periods=periods)

    def validate_strategies(self, evaluated: Iterable[Dict]) -> Dict:
        result = self.validator.validate(evaluated)
        self.repository.save_validated(result.get("validated", []))
        self.repository.archive(result.get("rejected", []))
        return result

    def promote_to_strategy_bank(self, validated_rows: Iterable[Dict]) -> List[str]:
        rows = [dict(row) for row in validated_rows if row.get("id")]
        promoted_ids: List[str] = []

        if not rows:
            return promoted_ids

        # Push into Strategy Bank in SHADOW stage.
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                registry = layer.bank_engine.registry
                for row in rows:
                    payload = self._to_registry_payload(row)
                    payload["stage"] = "SHADOW"
                    payload["active"] = False
                    registry.upsert(payload)
                    promoted_ids.append(payload["id"])
                registry.save()
            except Exception:
                promoted_ids = []

        # Inform Meta Brain for ranking/promotion flow.
        brain = self.meta_strategy_brain
        if brain:
            try:
                brain.promote_new_strategies(rows)
            except Exception:
                pass

        return promoted_ids

    def run_experiment(
        self,
        generate_count: int = 50,
        variants_per_base: int = 20,
        periods: int = 260,
    ) -> Dict:
        """Run full Alpha Factory cycle and return structured output."""
        base = self.run_strategy_generation(count=generate_count)
        mutated = self.run_mutation_pipeline(base, variants_per_base=variants_per_base)
        candidates = base + mutated
        evaluated = self.run_backtests(candidates, periods=periods)
        validation = self.validate_strategies(evaluated)

        promoted_ids: List[str] = []
        if not self.sandbox_mode:
            promoted_ids = self.promote_to_strategy_bank(validation.get("validated", []))

        return {
            "NEW_RESEARCH_STRATEGIES": [row.get("id") for row in candidates if row.get("id")],
            "VALIDATED_STRATEGIES": [row.get("id") for row in validation.get("validated", []) if row.get("id")],
            "REJECTED_STRATEGIES": [row.get("id") for row in validation.get("rejected", []) if row.get("id")],
            "PROMOTED_STRATEGIES": promoted_ids,
            "sandbox_mode": self.sandbox_mode,
        }

    def _to_registry_payload(self, row: Dict) -> Dict:
        metrics = dict(row.get("metrics", {}))
        return {
            "id": str(row.get("id")),
            "asset_class": row.get("asset_class", "stocks"),
            "timeframe": row.get("timeframe", "5m"),
            "category": row.get("category", row.get("family", "systematic")),
            "regime_preference": row.get(
                "regime_preference",
                ["TRENDING", "RANGING", "HIGH_VOL", "LOW_VOL", "CRASH"],
            ),
            "sharpe": float(metrics.get("sharpe", 0.0)),
            "profit_factor": float(metrics.get("profit_factor", 0.0)),
            "max_drawdown": float(metrics.get("max_dd", metrics.get("max_drawdown", 0.0))),
            "win_rate": float(metrics.get("win_rate", 0.0)),
            "expectancy": float(metrics.get("expectancy", 0.0)),
            "sample_size": int(metrics.get("sample_size", len(metrics.get("returns", [])))),
            "returns": list(metrics.get("returns", [])),
            "allocation_pct": 0.0,
            "correlation_cluster": "",
            "score": 0.0,
        }

