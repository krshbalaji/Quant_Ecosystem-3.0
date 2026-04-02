from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Literal, Optional


class SignalAggregator:
    """
    Aggregates strategy-level signals into symbol-level intents.
    """

    def __init__(self, method: Literal["majority_vote", "strength_weighted", "volatility_adjusted"] = "majority_vote", **kwargs):
        self.method = method

    def aggregate(self, signals: List[Dict], feature_engine=None) -> List[Dict]:
        by_symbol: Dict[str, List[Dict]] = defaultdict(list)
        for s in signals:
            sym = str(s.get("symbol", "")).strip()
            if not sym:
                continue
            by_symbol[sym].append(s)

        out: List[Dict] = []
        for symbol, bucket in by_symbol.items():
            if not bucket:
                continue
            aggregated = self._aggregate_symbol(symbol, bucket, feature_engine=feature_engine)
            if aggregated:
                out.append(aggregated)
        return out

    def _aggregate_symbol(self, symbol: str, bucket: List[Dict], feature_engine=None) -> Optional[Dict]:
        method = self.method
        if method == "strength_weighted":
            return self._strength_weighted(symbol, bucket)
        if method == "volatility_adjusted":
            return self._volatility_adjusted(symbol, bucket, feature_engine=feature_engine)
        return self._majority_vote(symbol, bucket)

    def _majority_vote(self, symbol: str, bucket: List[Dict]) -> Optional[Dict]:
        buys = [s for s in bucket if str(s.get("side", "")).upper() == "BUY"]
        sells = [s for s in bucket if str(s.get("side", "")).upper() == "SELL"]
        total = len(buys) + len(sells)
        if total == 0:
            return None
        if len(buys) > len(sells):
            side = "BUY"
            confidence = len(buys) / total
            sources = [s["strategy_id"] for s in buys]
        elif len(sells) > len(buys):
            side = "SELL"
            confidence = len(sells) / total
            sources = [s["strategy_id"] for s in sells]
        else:
            # Tie – no clear intent
            return None
        return {
            "symbol": symbol,
            "side": side,
            "confidence": float(confidence),
            "sources": sources,
        }

    def _strength_weighted(self, symbol: str, bucket: List[Dict]) -> Optional[Dict]:
        buy_strength = 0.0
        sell_strength = 0.0
        buy_sources = []
        sell_sources = []
        for s in bucket:
            side = str(s.get("side", "")).upper()
            strength = float(s.get("strength", 1.0))
            if side == "BUY":
                buy_strength += strength
                buy_sources.append(s["strategy_id"])
            elif side == "SELL":
                sell_strength += strength
                sell_sources.append(s["strategy_id"])
        total = buy_strength + sell_strength
        if total <= 0:
            return None
        if buy_strength > sell_strength:
            side = "BUY"
            confidence = buy_strength / total
            sources = buy_sources
        elif sell_strength > buy_strength:
            side = "SELL"
            confidence = sell_strength / total
            sources = sell_sources
        else:
            return None
        return {
            "symbol": symbol,
            "side": side,
            "confidence": float(confidence),
            "sources": sources,
        }

    def _volatility_adjusted(self, symbol: str, bucket: List[Dict], feature_engine=None) -> Optional[Dict]:
        base = self._strength_weighted(symbol, bucket)
        if not base:
            return None
        if feature_engine is None:
            return base
        vol = feature_engine.get_volatility(symbol) if hasattr(feature_engine, "get_volatility") else None
        if vol is None:
            return base
        # Simple volatility dampening: higher vol => lower confidence.
        adjusted_conf = base["confidence"] / (1.0 + float(vol))
        base["confidence"] = float(max(0.0, min(adjusted_conf, 1.0)))
        return base

