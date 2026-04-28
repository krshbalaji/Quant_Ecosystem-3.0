"""Opportunity ranking engine for Global Alpha Scanner."""

from __future__ import annotations

from typing import Dict, Iterable, List


class OpportunityRanker:
    """Scores and ranks opportunities by signal and market quality."""

    def __init__(
        self,
        w_signal: float = 0.4,
        w_volatility: float = 0.2,
        w_liquidity: float = 0.2,
        w_trend: float = 0.2, **kwargs
    ):
        self.w_signal = float(w_signal)
        self.w_volatility = float(w_volatility)
        self.w_liquidity = float(w_liquidity)
        self.w_trend = float(w_trend)

    def rank(self, opportunities: Iterable[Dict], top_n: int = 50) -> List[Dict]:
        """Return top ranked opportunities."""
        out = []
        for row in opportunities:
            item = dict(row)
            signal_strength = self._float(item.get("signal_strength", 0.0))
            volatility = self._float(item.get("volatility", 0.0))
            liquidity = self._float(item.get("liquidity_score", 0.5))
            spread = self._float(item.get("spread", 0.0))
            trend_quality = self._float(item.get("trend_quality", 0.0))

            volatility_score = self._volatility_score(volatility)
            liquidity_score = self._liquidity_score(liquidity, spread)
            trend_score = self._trend_score(trend_quality)

            score = (
                signal_strength * self.w_signal
                + volatility_score * self.w_volatility
                + liquidity_score * self.w_liquidity
                + trend_score * self.w_trend
            )
            item["score"] = round(score, 6)
            out.append(item)

        out.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)

        # -------------------------------
        # Correlation cap (max 2)
        # -------------------------------
        filtered = []
        cluster_counts = {}

        for row in out:
            cluster = str(
                row.get(
                    "correlation_cluster",
                    row.get("asset_class", "uncategorized")
                )
            ).strip()

            if cluster_counts.get(cluster, 0) >= 2:
                continue

            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
            filtered.append(row)


        # -------------------------------
        # Broker opportunity slots (max 5)
        # Serve best first
        # -------------------------------
        broker_counts = {}
        allocated = []

        for row in filtered:

            broker = str(
                row.get(
                    "preferred_broker",
                    row.get(
                        "broker",
                        "UNASSIGNED"
                    )
                )
            ).strip()

            if broker_counts.get(broker, 0) >= 5:
                continue

            broker_counts[broker] = broker_counts.get(broker,0) + 1

            row["dispatch_priority"] = len(allocated)+1
            row["broker_slot"] = broker_counts[broker]

            allocated.append(row)

            if len(allocated) >= max(1, int(top_n)):
                break


        return allocated

    def _volatility_score(self, vol: float) -> float:
        # Sweet spot around medium volatility; penalize very low/high.
        if vol <= 0:
            return 0.0
        if vol < 0.1:
            return 0.2
        if vol < 0.5:
            return 0.7
        if vol < 2.5:
            return 1.0
        if vol < 5.0:
            return 0.65
        return 0.35

    def _liquidity_score(self, liquidity: float, spread: float) -> float:
        spread_penalty = min(max(spread * 50.0, 0.0), 1.0)
        raw = min(max(liquidity, 0.0), 1.0) * (1.0 - spread_penalty)
        return max(0.0, min(1.0, raw))

    def _trend_score(self, trend_quality: float) -> float:
        return max(0.0, min(1.0, trend_quality / 10.0))

    def _float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

