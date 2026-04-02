"""Route regimes to target strategy families for portfolio expansion."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set


class RegimeStrategyRouter:
    """Maps regime states to strategy families and filters candidates."""

    def __init__(self, regime_map: Dict[str, Iterable[str]] | None = None, **kwargs):
        default = {
            "TRENDING_BULL": {"trend_following", "breakout"},
            "TRENDING_BEAR": {"trend_following", "breakout"},
            "RANGE_BOUND": {"mean_reversion", "statistical_arbitrage"},
            "HIGH_VOLATILITY": {"volatility", "options"},
            "LOW_VOLATILITY": {"mean_reversion", "statistical_arbitrage", "trend_following"},
            "CRASH_EVENT": {"volatility", "options", "trend_following"},
        }
        source = regime_map or default
        self.regime_map: Dict[str, Set[str]] = {
            str(regime).upper(): {str(f).strip().lower() for f in families if str(f).strip()}
            for regime, families in source.items()
        }

    def families_for_regime(self, regime: str) -> Set[str]:
        return set(self.regime_map.get(str(regime).upper(), set()))

    def filter_candidates(self, regime: str, strategy_rows: Iterable[Dict]) -> List[Dict]:
        target = self.families_for_regime(regime)
        if not target:
            return list(strategy_rows)

        out = []
        for row in strategy_rows:
            family = str(row.get("family", row.get("category", "trend_following"))).strip().lower()
            if family in target:
                out.append(row)
                continue
            # Keep generic/systematic strategies as portable candidates.
            if family in {"systematic", "generic", "core"}:
                out.append(row)
        return out

