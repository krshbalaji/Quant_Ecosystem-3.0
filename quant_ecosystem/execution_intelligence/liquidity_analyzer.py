"""Liquidity analysis for execution intelligence."""

from __future__ import annotations

from typing import Dict


class LiquidityAnalyzer:
    """Computes liquidity score from market microstructure indicators."""

    def analyze(self, volume: float, bid_ask_depth: float, recent_trade_activity: float) -> Dict:
        v = max(0.0, float(volume))
        d = max(0.0, float(bid_ask_depth))
        t = max(0.0, float(recent_trade_activity))

        # Simple bounded components.
        volume_score = min(1.0, v / 100000.0)
        depth_score = min(1.0, d / 10000.0)
        activity_score = min(1.0, t / 1000.0)

        liquidity_score = (0.45 * volume_score) + (0.35 * depth_score) + (0.20 * activity_score)
        bucket = "LOW"
        if liquidity_score >= 0.7:
            bucket = "HIGH"
        elif liquidity_score >= 0.4:
            bucket = "MEDIUM"

        return {
            "liquidity_score": round(liquidity_score, 6),
            "bucket": bucket,
            "volume_score": round(volume_score, 6),
            "depth_score": round(depth_score, 6),
            "activity_score": round(activity_score, 6),
        }

