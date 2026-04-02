"""Slippage estimator for microstructure simulation."""

from __future__ import annotations

from typing import Dict


class SlippageModel:
    """Computes slippage using volatility, size, and liquidity."""

    def __init__(self, multiplier: float = 1.0, **kwargs):
        self.multiplier = max(0.1, float(multiplier))

    def estimate(self, volatility: float, order_size: float, liquidity_score: float) -> Dict:
        vol = max(0.0, float(volatility))
        qty = max(0.0, float(order_size))
        liq = max(0.01, min(1.0, float(liquidity_score)))

        size_factor = min(5.0, 1.0 + (qty / 200.0))
        liquidity_penalty = 1.0 / liq

        # slippage = volatility * size_factor * liquidity_penalty
        raw = vol * size_factor * liquidity_penalty
        slip_pct = min(0.03, raw * 0.0012 * self.multiplier)

        return {
            "slippage_pct": round(slip_pct, 8),
            "size_factor": round(size_factor, 6),
            "liquidity_penalty": round(liquidity_penalty, 6),
        }

