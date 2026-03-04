"""Liquidity monitor for market pulse."""

from __future__ import annotations

from typing import Dict


class LiquidityMonitor:
    """Detects liquidity drops and returns liquidity score."""

    def __init__(self, drop_threshold: float = 0.35):
        self.drop_threshold = max(0.05, min(0.95, float(drop_threshold)))

    def evaluate(self, snapshot: Dict) -> Dict:
        volume = self._f(snapshot.get("volume", 0.0))
        bid_depth = self._f(snapshot.get("bid_depth", snapshot.get("depth_bid", 0.0)))
        ask_depth = self._f(snapshot.get("ask_depth", snapshot.get("depth_ask", 0.0)))
        spread = self._f(snapshot.get("spread", 0.0))

        vol_norm = min(1.0, volume / 500000.0)
        depth_norm = min(1.0, (bid_depth + ask_depth) / 250000.0)
        spread_penalty = min(1.0, spread * 20.0)
        liquidity_score = max(0.0, min(1.0, (0.45 * vol_norm) + (0.45 * depth_norm) - (0.10 * spread_penalty)))

        triggered = liquidity_score <= self.drop_threshold
        strength = min(1.0, max(0.0, (self.drop_threshold - liquidity_score) / max(self.drop_threshold, 1e-9)))

        return {
            "triggered": bool(triggered),
            "event_type": "LIQUIDITY_DROP",
            "strength": round(strength, 6),
            "liquidity_score": round(liquidity_score, 6),
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

