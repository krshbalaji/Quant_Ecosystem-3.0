"""Global regime classifier."""

from __future__ import annotations

from typing import Dict


class GlobalRegimeClassifier:
    """Classifies macro regimes from cross-asset and liquidity features."""

    def classify(self, cross_asset: Dict, liquidity: Dict, macro_inputs: Dict | None = None) -> Dict:
        macro = dict(macro_inputs or {})
        stress = self._f(cross_asset.get("market_stress_score", 0.0))
        liq_score = self._f(liquidity.get("liquidity_score", 0.5))
        inflation = self._f(macro.get("inflation_trend", 0.0))
        growth = self._f(macro.get("growth_trend", 0.0))
        vol_state = str(macro.get("volatility_state", "NORMAL")).upper()

        if stress > 0.75 or liq_score < 0.25:
            regime = "RISK_OFF"
        elif inflation > 0.5 and growth >= 0.0:
            regime = "INFLATION"
        elif growth < -0.4 and inflation < 0.2:
            regime = "DEFLATION"
        elif vol_state in {"HIGH", "EXPANSION"} or stress > 0.6:
            regime = "VOLATILITY_EXPANSION"
        else:
            regime = "RISK_ON"

        if regime in {"RISK_OFF", "VOLATILITY_EXPANSION"}:
            pref = "DEFENSIVE"
        elif regime == "INFLATION":
            pref = "MOMENTUM_COMMODITIES"
        elif regime == "DEFLATION":
            pref = "MEAN_REVERSION_RATES"
        else:
            pref = "TREND_GROWTH"

        return {
            "regime": regime,
            "volatility_state": vol_state,
            "liquidity_state": str(liquidity.get("liquidity_state", "NEUTRAL")).upper(),
            "preferred_strategy_type": pref,
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

