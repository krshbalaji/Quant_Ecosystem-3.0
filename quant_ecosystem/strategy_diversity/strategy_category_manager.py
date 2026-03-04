"""Strategy category normalization and classification."""

from __future__ import annotations

from typing import Dict


class StrategyCategoryManager:
    """Maps strategies into a stable category taxonomy.

    Supported canonical categories:
    - momentum
    - mean_reversion
    - breakout
    - volatility
    - stat_arb
    """

    CANONICAL = ("momentum", "mean_reversion", "breakout", "volatility", "stat_arb")

    _ALIASES = {
        "momentum": "momentum",
        "trend": "momentum",
        "trend_following": "momentum",
        "mean_reversion": "mean_reversion",
        "meanrev": "mean_reversion",
        "mean-reversion": "mean_reversion",
        "breakout": "breakout",
        "volatility": "volatility",
        "vol": "volatility",
        "options_volatility": "volatility",
        "stat_arb": "stat_arb",
        "stat-arb": "stat_arb",
        "statistical_arbitrage": "stat_arb",
        "pairs_trading": "stat_arb",
        "pairs": "stat_arb",
    }

    def classify(self, row: Dict) -> str:
        """Return canonical category for a strategy row."""
        category = self._clean(
            row.get("category")
            or row.get("family")
            or row.get("strategy_type")
            or row.get("type")
            or ""
        )
        if category in self._ALIASES:
            return self._ALIASES[category]

        # Fallback by name/id semantics.
        text = " ".join(
            [
                self._clean(row.get("id", "")),
                self._clean(row.get("name", "")),
                self._clean(row.get("entry_logic", "")),
            ]
        )
        if "mean" in text and "reversion" in text:
            return "mean_reversion"
        if "breakout" in text:
            return "breakout"
        if "vix" in text or "vol" in text or "atr" in text:
            return "volatility"
        if "pair" in text or "arb" in text:
            return "stat_arb"
        return "momentum"

    def enrich(self, row: Dict) -> Dict:
        """Return a copy of row with normalized category."""
        out = dict(row)
        out["diversity_category"] = self.classify(row)
        return out

    def _clean(self, value) -> str:
        return str(value or "").strip().lower()

