"""Meta Strategy Brain.

A strategy-of-strategies layer that governs activation, lifecycle, promotion,
retirement, and portfolio balance without modifying existing trading modules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.meta_strategy.strategy_diversification_engine import (
    StrategyDiversificationEngine,
)
from quant_ecosystem.meta_strategy.strategy_lifecycle_manager import (
    StrategyLifecycleManager,
)
from quant_ecosystem.meta_strategy.strategy_retirement_engine import (
    StrategyRetirementEngine,
)
from quant_ecosystem.meta_strategy.strategy_scoring_engine import StrategyScoringEngine


class MetaStrategyBrain:
    """Top-level meta controller for strategy ecosystem decisions."""

    def __init__(
        self,
        strategy_bank_layer=None,
        capital_allocator_engine=None,
        mutation_layer=None,
        strategy_selector=None,
        scoring_engine: Optional[StrategyScoringEngine] = None,
        lifecycle_manager: Optional[StrategyLifecycleManager] = None,
        diversification_engine: Optional[StrategyDiversificationEngine] = None,
        retirement_engine: Optional[StrategyRetirementEngine] = None, **kwargs
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.capital_allocator_engine = capital_allocator_engine
        self.mutation_layer = mutation_layer
        self.strategy_selector = strategy_selector
        self.scoring_engine = scoring_engine or StrategyScoringEngine()
        self.lifecycle_manager = lifecycle_manager or StrategyLifecycleManager()
        self.diversification_engine = diversification_engine or StrategyDiversificationEngine()
        self.retirement_engine = retirement_engine or StrategyRetirementEngine()
        self.last_decisions: Dict = {}

    def evaluate_strategy_ecosystem(
        self,
        regime: str,
        strategy_rows: Optional[Iterable[Dict]] = None,
        mutated_candidates: Optional[Iterable[Dict]] = None,
        max_active: int = 5,
    ) -> Dict:
        """Runs full meta-brain cycle and returns portfolio-level decisions."""
        regime_key = str(regime or "RANGE_BOUND").upper()
        rows = list(strategy_rows) if strategy_rows is not None else self._registry_rows()

        scored = self.score_strategies(rows)
        with_lifecycle = self.adjust_strategy_lifecycle(scored)
        diversified = self.rebalance_strategy_portfolio(with_lifecycle, max_active=max_active)
        promoted = self.promote_new_strategies(mutated_candidates or [])
        retired = self.retire_underperforming_strategies(diversified["active"] + diversified["reduced"])

        active, reduced, retired_final = self._merge_retirement(
            diversified["active"],
            diversified["reduced"],
            retired["retired"],
        )
        self._persist_rows(active + reduced + retired_final)
        self._rebalance_capital(regime_key, active)

        decisions = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "regime": regime_key,
            "ACTIVE_STRATEGIES": [row.get("id") for row in active if row.get("id")],
            "REDUCED_STRATEGIES": [row.get("id") for row in reduced if row.get("id")],
            "RETIRED_STRATEGIES": [row.get("id") for row in retired_final if row.get("id")],
            "PROMOTED_STRATEGIES": [row.get("id") for row in promoted if row.get("id")],
            "scores": {str(row.get("id")): float(row.get("meta_score", 0.0)) for row in active + reduced},
            "clusters": diversified.get("clusters", {}),
        }
        self.last_decisions = decisions
        return decisions

    def score_strategies(self, strategy_rows: Iterable[Dict]) -> List[Dict]:
        """Scores all strategies with dynamic meta-scoring."""
        return self.scoring_engine.score_batch(strategy_rows)

    def adjust_strategy_lifecycle(self, strategy_rows: Iterable[Dict]) -> List[Dict]:
        """Applies lifecycle transitions based on scored outcomes."""
        out = []
        for row in strategy_rows:
            item = dict(row)
            next_stage, reason = self.lifecycle_manager.transition(item)
            item["stage"] = next_stage
            item["lifecycle_reason"] = reason
            out.append(item)
        return out

    def rebalance_strategy_portfolio(self, strategy_rows: Iterable[Dict], max_active: int = 5) -> Dict:
        """Selects active/reduced sets using diversification constraints."""
        ranked = sorted(strategy_rows, key=lambda row: float(row.get("meta_score", 0.0)), reverse=True)
        diversified = self.diversification_engine.select_diversified(ranked, max_active=max_active)
        for row in diversified["active"]:
            row["active"] = True
            row["stage"] = "LIVE" if str(row.get("stage", "")).upper() in {"LIVE", "PAPER"} else row.get("stage")
        for row in diversified["reduced"]:
            row["active"] = False
            if str(row.get("stage", "")).upper() == "LIVE":
                row["stage"] = "REDUCED"
        return diversified

    def promote_new_strategies(self, candidates: Iterable[Dict]) -> List[Dict]:
        """Promotes superior mutation candidates to SHADOW stage."""
        rows = self._registry_rows()
        baseline = max([float(row.get("meta_score", 0.0)) for row in rows], default=0.0)
        promoted: List[Dict] = []
        for candidate in candidates or []:
            item = self._normalize_mutation_candidate(candidate)
            item["meta_score"] = self.scoring_engine.score(item)
            if item["meta_score"] >= max(0.55, baseline):
                item["stage"] = "SHADOW"
                item["active"] = False
                item["promotion_reason"] = "mutation_superior"
                promoted.append(item)
        if promoted:
            self._persist_rows(promoted)
        return promoted

    def retire_underperforming_strategies(self, strategy_rows: Iterable[Dict]) -> Dict:
        """Retires underperforming strategies and archives them."""
        return self.retirement_engine.evaluate(strategy_rows)

    def run_mutation_cycle(self) -> List[Dict]:
        """Optionally triggers mutation layer and returns normalized candidates."""
        layer = self.mutation_layer
        if not (layer and hasattr(layer, "is_enabled") and layer.is_enabled()):
            return []
        source_rows = self._registry_rows()
        produced = layer.run(source_rows)
        out = []
        for candidate in produced:
            out.append(self._normalize_mutation_candidate(candidate))
        return out

    def _rebalance_capital(self, regime: str, active_rows: List[Dict]) -> None:
        allocator = self.capital_allocator_engine
        if allocator is None:
            return
        try:
            allocator.rebalance(
                regime=regime,
                strategy_rows=active_rows,
                capital_available_pct=100.0,
                current_drawdown_pct=0.0,
                force=True,
            )
        except Exception:
            return

    def _persist_rows(self, rows: Iterable[Dict]) -> None:
        layer = self.strategy_bank_layer
        if not (layer and hasattr(layer, "is_enabled") and layer.is_enabled()):
            return
        try:
            registry = layer.bank_engine.registry
        except Exception:
            return
        for row in rows:
            if not row.get("id"):
                continue
            registry.upsert(dict(row))
        registry.save()

    def _registry_rows(self) -> List[Dict]:
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                return list(layer.registry_rows())
            except Exception:
                return []
        return []

    def _normalize_mutation_candidate(self, candidate: Dict) -> Dict:
        # Handles mutation outputs from quant_ecosystem.strategy_bank.mutation.mutation_engine.
        metrics = dict(candidate.get("metrics", {}))
        sid = candidate.get("id")
        if not sid:
            sid = (
                candidate.get("dna", {}).get("id")
                if isinstance(candidate.get("dna"), dict)
                else None
            )
        if not sid:
            sid = f"mut_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        return {
            "id": sid,
            "name": sid,
            "category": candidate.get("category", "systematic"),
            "family": candidate.get("family", candidate.get("category", "systematic")),
            "asset_class": candidate.get("asset_class", candidate.get("dna", {}).get("asset_class", "stocks")),
            "timeframe": candidate.get("timeframe", candidate.get("dna", {}).get("timeframe", "5m")),
            "stage": str(candidate.get("stage", "RESEARCH")).upper(),
            "metrics": metrics,
            "sharpe": float(metrics.get("sharpe", 0.0)),
            "profit_factor": float(metrics.get("profit_factor", 0.0)),
            "expectancy": float(metrics.get("expectancy", 0.0)),
            "win_rate": float(metrics.get("win_rate", 0.0)),
            "max_drawdown": float(metrics.get("max_dd", metrics.get("max_drawdown", 0.0))),
            "returns": list(metrics.get("returns", [])),
            "active": False,
        }

    def _merge_retirement(self, active: List[Dict], reduced: List[Dict], retired: List[Dict]):
        retired_ids = {str(row.get("id")) for row in retired if row.get("id")}
        active_new = [row for row in active if str(row.get("id")) not in retired_ids]
        reduced_new = [row for row in reduced if str(row.get("id")) not in retired_ids]
        return active_new, reduced_new, retired

