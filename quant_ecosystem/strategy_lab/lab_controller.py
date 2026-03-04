"""Orchestration controller for the Self-Evolving Strategy Lab."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from quant_ecosystem.strategy_lab.backtest_engine import BacktestEngine
from quant_ecosystem.strategy_lab.mutation_pipeline import MutationPipeline
from quant_ecosystem.strategy_lab.strategy_generator import StrategyGenerator
from quant_ecosystem.strategy_lab.strategy_repository import StrategyRepository
from quant_ecosystem.strategy_lab.strategy_validator import StrategyValidator


class StrategyLabController:
    """Runs end-to-end strategy generation/mutation/backtest/validation pipeline."""

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
        sandbox_mode: bool = True,
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.mutation_layer = mutation_layer
        self.meta_strategy_brain = meta_strategy_brain
        self.generator = generator or StrategyGenerator()
        self.mutation_pipeline = mutation_pipeline or MutationPipeline(mutation_layer=mutation_layer)
        self.backtest_engine = backtest_engine or BacktestEngine()
        self.validator = validator or StrategyValidator()
        self.repository = repository or StrategyRepository()
        self.sandbox_mode = bool(sandbox_mode)

    def run_strategy_generation(self, count: int = 50) -> List[Dict]:
        rows = self.generator.generate(count=count)
        self.repository.save_research(rows)
        return rows

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

