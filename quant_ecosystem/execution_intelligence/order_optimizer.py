"""Order optimization logic for execution intelligence."""

from __future__ import annotations

from typing import Dict

from quant_ecosystem.execution_intelligence.order_slicer import OrderSlicer


class OrderOptimizer:
    """Selects order type and slicing strategy from execution context."""

    def __init__(self, slicer: OrderSlicer | None = None):
        self.slicer = slicer or OrderSlicer()

    def optimize(
        self,
        symbol: str,
        side: str,
        quantity: int,
        spread: float,
        liquidity_score: float,
        expected_slippage: float,
        execution_policy: str,
    ) -> Dict:
        qty = max(0, int(quantity))
        spread_v = max(0.0, float(spread))
        liq = max(0.0, min(1.0, float(liquidity_score)))
        slip = max(0.0, float(expected_slippage))
        policy = str(execution_policy or "LOW_SLIPPAGE_MODE").upper()

        order_type = "market"
        method = "equal"
        slice_count = 1

        # Core rules.
        if spread_v > 0.15 or slip > 6.0:
            order_type = "limit"
        if qty >= 50 or (liq < 0.4 and qty >= 20):
            slice_count = min(20, max(2, qty // 10))
            method = "TWAP"
            order_type = "TWAP"
        if policy == "STEALTH_EXECUTION_MODE":
            if qty >= 30:
                order_type = "iceberg"
                method = "equal"
                slice_count = min(15, max(3, qty // 8))
            else:
                order_type = "limit"
        elif policy == "FAST_EXECUTION_MODE":
            order_type = "market" if spread_v <= 0.35 else "limit"
            method = "equal"
            slice_count = 1 if qty < 100 else min(8, qty // 20)

        slices = self.slicer.slice_order(qty, method=method, slice_count=slice_count)
        return {
            "symbol": str(symbol),
            "side": str(side).upper(),
            "order_type": order_type,
            "quantity": qty,
            "slice_count": len(slices),
            "slices": slices,
            "expected_slippage": round(slip, 6),
            "execution_policy": policy,
        }

