"""Strategy portfolio expansion builder.

Builds a diversified, regime-aware strategy portfolio from Strategy Bank rows
and can optionally coordinate with the autonomous strategy selector.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from quant_ecosystem.strategy_portfolio.portfolio_optimizer import PortfolioOptimizer
from quant_ecosystem.strategy_portfolio.regime_strategy_router import RegimeStrategyRouter


class PortfolioBuilder:
    """Assembles a multi-family strategy portfolio for a given regime."""

    def __init__(
        self,
        strategy_bank_layer=None,
        strategy_selector=None,
        regime_router: Optional[RegimeStrategyRouter] = None,
        optimizer: Optional[PortfolioOptimizer] = None,
        max_strategies: int = 5,
        correlation_threshold: float = 0.7,
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.strategy_selector = strategy_selector
        self.regime_router = regime_router or RegimeStrategyRouter()
        self.optimizer = optimizer or PortfolioOptimizer(
            max_strategies=max_strategies,
            correlation_threshold=correlation_threshold,
        )
        self.max_strategies = max(1, int(max_strategies))
        self.correlation_threshold = max(0.0, min(0.99, float(correlation_threshold)))

    def build_portfolio(
        self,
        regime: str,
        strategy_rows: Optional[Iterable[Dict]] = None,
        max_strategies: Optional[int] = None,
    ) -> Dict:
        """Returns a diversified portfolio plan for the given market regime."""
        regime_key = str(regime or "RANGE_BOUND").upper()
        rows = list(strategy_rows) if strategy_rows is not None else self._fetch_registry_rows()
        if not rows:
            return self._empty_result(regime_key)

        routed = self.regime_router.filter_candidates(regime_key, rows)
        optimized = self.optimizer.optimize(
            routed,
            max_strategies=max_strategies or self.max_strategies,
            correlation_threshold=self.correlation_threshold,
        )

        family_mix = self._family_mix(optimized)
        weights = self._equal_weight_map(optimized)

        return {
            "regime": regime_key,
            "candidate_count": len(rows),
            "routed_count": len(routed),
            "selected_count": len(optimized),
            "families": self.regime_router.families_for_regime(regime_key),
            "family_mix": family_mix,
            "weights": weights,
            "selected": optimized,
        }

    def build_and_select(
        self,
        regime: str,
        strategy_rows: Optional[Iterable[Dict]] = None,
        risk_limits: Dict | None = None,
        capital_available_pct: float = 100.0,
    ) -> Dict:
        """Builds a portfolio and asks selector to activate the chosen subset."""
        plan = self.build_portfolio(regime=regime, strategy_rows=strategy_rows)
        selector = self.strategy_selector
        if selector is None:
            plan["selector"] = {"used": False, "reason": "MISSING_SELECTOR"}
            return plan

        selected_ids = [str(row.get("id")) for row in plan.get("selected", []) if row.get("id")]
        if not selected_ids:
            plan["selector"] = {"used": True, "activation": {"active_ids": []}}
            return plan

        # Reuse selector's activation flow without changing existing selector code.
        activation = selector.activation_manager.apply_selection(
            selected_ids=selected_ids,
            available_ids=[row.get("id") for row in self._fetch_registry_rows()],
        )
        plan["selector"] = {
            "used": True,
            "risk_limits": dict(risk_limits or {}),
            "capital_available_pct": float(capital_available_pct),
            "activation": activation,
        }
        return plan

    def _fetch_registry_rows(self) -> List[Dict]:
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                return list(layer.registry_rows())
            except Exception:
                return []
        return []

    def _family_mix(self, rows: Iterable[Dict]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for row in rows:
            family = str(row.get("family", row.get("category", "systematic"))).strip().lower()
            family = family or "systematic"
            out[family] = out.get(family, 0) + 1
        return out

    def _equal_weight_map(self, rows: Iterable[Dict]) -> Dict[str, float]:
        rows_list = [row for row in rows if row.get("id")]
        if not rows_list:
            return {}
        raw = 100.0 / len(rows_list)
        return {str(row["id"]): round(raw, 4) for row in rows_list}

    def _empty_result(self, regime: str) -> Dict:
        return {
            "regime": regime,
            "candidate_count": 0,
            "routed_count": 0,
            "selected_count": 0,
            "families": self.regime_router.families_for_regime(regime),
            "family_mix": {},
            "weights": {},
            "selected": [],
        }
