"""Macro signal generation for strategic guidance."""

from __future__ import annotations

from typing import Dict, List


class MacroSignalEngine:
    """Generates high-level strategic macro signals."""

    def generate(self, regime_row: Dict, cross_asset: Dict, liquidity: Dict) -> Dict:
        regime = str(regime_row.get("regime", "RISK_ON")).upper()
        signals: List[Dict] = []

        if regime == "RISK_ON":
            signals.append({"signal": "SECTOR_ROTATION", "direction": "CYCLICALS_OVER_DEFENSIVES", "strength": 0.65})
            signals.append({"signal": "RISK_APPETITE", "direction": "HIGH", "strength": 0.7})
        elif regime == "RISK_OFF":
            signals.append({"signal": "SECTOR_ROTATION", "direction": "DEFENSIVES_OVER_CYCLICALS", "strength": 0.8})
            signals.append({"signal": "RISK_APPETITE", "direction": "LOW", "strength": 0.85})
        elif regime == "INFLATION":
            signals.append({"signal": "MACRO_TREND_SHIFT", "direction": "COMMODITIES_UP", "strength": 0.75})
        elif regime == "DEFLATION":
            signals.append({"signal": "MACRO_TREND_SHIFT", "direction": "DURATION_ASSETS_UP", "strength": 0.7})
        elif regime == "VOLATILITY_EXPANSION":
            signals.append({"signal": "RISK_APPETITE", "direction": "REDUCE_GROSS_EXPOSURE", "strength": 0.9})

        stress = float(cross_asset.get("market_stress_score", 0.0) or 0.0)
        liq = float(liquidity.get("liquidity_score", 0.0) or 0.0)
        confidence = max(0.0, min(1.0, 0.5 + (stress * 0.25) + ((1.0 - liq) * 0.25)))
        return {
            "signals": signals,
            "confidence": round(confidence, 6),
            "macro_trend": regime,
        }

