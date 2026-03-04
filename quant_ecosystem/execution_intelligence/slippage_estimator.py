"""Slippage estimation for execution decisions."""

from __future__ import annotations

from typing import Dict


class SlippageEstimator:
    """Estimate expected slippage from spread, volatility, size, and liquidity."""

    def estimate(
        self,
        spread: float,
        volatility: float,
        order_size: float,
        liquidity_depth: float,
    ) -> Dict:
        s = max(0.0, float(spread))
        v = max(0.0, float(volatility))
        q = max(0.0, float(order_size))
        d = max(1.0, float(liquidity_depth))

        # bps-style synthetic slippage model.
        spread_component = s * 0.5
        vol_component = v * 0.15
        size_component = (q / d) * 8.0
        expected = spread_component + vol_component + size_component

        severity = "LOW"
        if expected >= 12.0:
            severity = "HIGH"
        elif expected >= 5.0:
            severity = "MEDIUM"

        return {
            "expected_slippage": round(expected, 6),
            "severity": severity,
            "components": {
                "spread": round(spread_component, 6),
                "volatility": round(vol_component, 6),
                "size": round(size_component, 6),
            },
        }

