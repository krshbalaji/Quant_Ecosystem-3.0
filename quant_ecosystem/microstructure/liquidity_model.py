"""Liquidity estimation model for microstructure simulation."""

from __future__ import annotations

from typing import Dict


class LiquidityModel:
    """Estimates available liquidity from volume/depth/flow."""

    def estimate(self, volume: float, market_depth: float, trade_flow: float) -> Dict:
        volume = max(0.0, float(volume))
        market_depth = max(0.0, float(market_depth))
        trade_flow = max(0.0, float(trade_flow))

        # Normalize signals into [0, 1] range.
        vol_norm = min(1.0, volume / 500000.0)
        depth_norm = min(1.0, market_depth / 200000.0)
        flow_norm = min(1.0, trade_flow / 100000.0)

        # Depth and volume dominate instantaneous execution ability.
        liquidity_score = (0.45 * depth_norm) + (0.4 * vol_norm) + (0.15 * flow_norm)
        liquidity_score = max(0.01, min(1.0, liquidity_score))

        return {
            "liquidity_score": round(liquidity_score, 6),
            "volume_norm": round(vol_norm, 6),
            "depth_norm": round(depth_norm, 6),
            "flow_norm": round(flow_norm, 6),
        }

