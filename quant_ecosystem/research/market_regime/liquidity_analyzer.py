"""Liquidity analysis module for market regime detection."""

from __future__ import annotations

from typing import Dict, List


class LiquidityAnalyzer:
    """Computes liquidity score from volume, spread, and order-flow proxies."""

    def __init__(self, volume_window: int = 20, **kwargs):
        self.volume_window = max(5, int(volume_window))

    def analyze(self, market_data: Dict) -> Dict:
        volume = self._series(market_data, "volume")
        spreads = self._series(market_data, "spread") or self._series(market_data, "bid_ask_spread")
        ofi_series = self._series(market_data, "order_flow_imbalance")

        volume_spike = self._volume_spike_ratio(volume)
        spread_stability = self._spread_stability(spreads)
        order_flow_imbalance = self._order_flow_imbalance(ofi_series, market_data)

        score = (
            (35.0 * min(volume_spike, 2.0) / 2.0)
            + (40.0 * spread_stability)
            + (25.0 * max(0.0, 1.0 - abs(order_flow_imbalance)))
        )

        return {
            "volume_spike": round(volume_spike, 4),
            "spread_stability": round(spread_stability, 4),
            "order_flow_imbalance": round(order_flow_imbalance, 4),
            "liquidity_score": round(max(0.0, min(score, 100.0)), 4),
        }

    def _series(self, data: Dict, key: str) -> List[float]:
        values = data.get(key, [])
        if isinstance(values, list) and values:
            return [float(v) for v in values]
        return []

    def _volume_spike_ratio(self, volume: List[float]) -> float:
        if len(volume) < self.volume_window + 1:
            return 1.0
        baseline = sum(volume[-(self.volume_window + 1):-1]) / self.volume_window
        if baseline <= 0:
            return 1.0
        return volume[-1] / baseline

    def _spread_stability(self, spreads: List[float]) -> float:
        if len(spreads) < 5:
            return 0.8
        mean = sum(spreads) / len(spreads)
        if mean == 0:
            return 1.0
        var = sum((x - mean) ** 2 for x in spreads) / len(spreads)
        cv = (var ** 0.5) / abs(mean)
        return max(0.0, min(1.0, 1.0 - min(cv, 1.0)))

    def _order_flow_imbalance(self, ofi_series: List[float], market_data: Dict) -> float:
        if ofi_series:
            return max(-1.0, min(1.0, ofi_series[-1]))

        buy_volume = float(market_data.get("buy_volume", 0.0))
        sell_volume = float(market_data.get("sell_volume", 0.0))
        den = buy_volume + sell_volume
        if den <= 0:
            return 0.0
        return max(-1.0, min(1.0, (buy_volume - sell_volume) / den))
