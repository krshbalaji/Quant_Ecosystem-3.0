"""Regime to strategy-type mapping for autonomous selection."""

from __future__ import annotations

from typing import Dict, Iterable, Set


class RegimeStrategyMap:
    """Maps market regimes to preferred strategy categories."""

    def __init__(self, mapping: Dict[str, Iterable[str]] | None = None):
        default = {
            "TRENDING_BULL": {"trend_following", "breakout", "momentum"},
            "TRENDING_BEAR": {"trend_following", "breakout", "momentum"},
            "RANGE_BOUND": {"mean_reversion", "market_neutral"},
            "HIGH_VOLATILITY": {"volatility_strategies", "breakout"},
            "LOW_VOLATILITY": {"mean_reversion", "carry", "momentum"},
            "CRASH_EVENT": {"defensive", "volatility_strategies"},
        }
        source = mapping or default
        self.mapping: Dict[str, Set[str]] = {
            str(regime).upper(): {str(cat).strip().lower() for cat in categories if str(cat).strip()}
            for regime, categories in source.items()
        }

    def strategy_types_for_regime(self, regime: str) -> Set[str]:
        key = str(regime or "").upper()
        return set(self.mapping.get(key, set()))

    def matches(self, strategy_row: Dict, regime: str) -> bool:
        allowed = self.strategy_types_for_regime(regime)
        if not allowed:
            return True
        category = str(strategy_row.get("category", "systematic")).strip().lower()
        if category in {"systematic", "generic", "core"}:
            return True
        return category in allowed
