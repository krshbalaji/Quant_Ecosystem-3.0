"""Signal confidence scoring engine."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional


class SignalConfidenceEngine:
    """Converts raw/binary signals into confidence-scored signals."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_confidence: float = 0.0, **kwargs
    ):
        default_weights = {
            "trend_strength": 0.3,
            "momentum_strength": 0.2,
            "volume_confirmation": 0.2,
            "volatility_alignment": 0.2,
            "liquidity_score": 0.1,
        }
        self.weights = self._normalize_weights(weights or default_weights)
        self.min_confidence = max(0.0, min(1.0, float(min_confidence)))

    def score_signal(self, signal: Dict, context: Optional[Dict] = None) -> Dict:
        """Return one scored signal payload."""
        ctx = context or {}
        row = dict(signal)

        trend_strength = self._clip01(self._value(row, ctx, "trend_strength"))
        momentum_strength = self._clip01(self._value(row, ctx, "momentum_strength"))
        volume_confirmation = self._clip01(self._value(row, ctx, "volume_confirmation"))
        volatility_alignment = self._clip01(self._value(row, ctx, "volatility_alignment"))
        liquidity_score = self._clip01(self._value(row, ctx, "liquidity_score"))

        confidence = (
            trend_strength * self.weights["trend_strength"]
            + momentum_strength * self.weights["momentum_strength"]
            + volume_confirmation * self.weights["volume_confirmation"]
            + volatility_alignment * self.weights["volatility_alignment"]
            + liquidity_score * self.weights["liquidity_score"]
        )
        confidence = round(self._clip01(confidence), 6)

        row["confidence_score"] = confidence
        row["confidence_components"] = {
            "trend_strength": round(trend_strength, 6),
            "momentum_strength": round(momentum_strength, 6),
            "volume_confirmation": round(volume_confirmation, 6),
            "volatility_alignment": round(volatility_alignment, 6),
            "liquidity_score": round(liquidity_score, 6),
        }
        row["confidence_formula"] = "trend*0.3 + momentum*0.2 + volume*0.2 + volatility*0.2 + liquidity*0.1"
        row["eligible"] = confidence >= self.min_confidence
        row.setdefault("signal_type", str(row.get("side", row.get("signal_type", "UNKNOWN"))).upper())
        row.setdefault("symbol", str(row.get("symbol", "")))
        return row

    def score_batch(self, signals: Iterable[Dict], context_map: Optional[Dict[str, Dict]] = None) -> List[Dict]:
        """Score a list of signals."""
        out = []
        cmap = context_map or {}
        for row in signals:
            symbol = str(row.get("symbol", ""))
            ctx = cmap.get(symbol, cmap.get("*", {}))
            out.append(self.score_signal(row, context=ctx))
        return out

    def publish_to_engines(
        self,
        scored_signals: Iterable[Dict],
        strategy_selector=None,
        portfolio_ai=None,
        execution_engine=None,
    ) -> Dict:
        """Broadcast scored signals to selector/portfolio/execution layers."""
        rows = list(scored_signals)
        payload = {"scored_signals": rows, "count": len(rows)}

        if strategy_selector is not None:
            try:
                setattr(strategy_selector, "last_scored_signals", rows)
            except Exception:
                pass
        if portfolio_ai is not None:
            try:
                setattr(portfolio_ai, "last_scored_signals", rows)
            except Exception:
                pass
        if execution_engine is not None:
            try:
                setattr(execution_engine, "last_scored_signals", rows)
            except Exception:
                pass
        return payload

    def _value(self, signal: Dict, context: Dict, key: str) -> float:
        if key in signal:
            return self._to_float(signal.get(key), 0.0)
        if key in context:
            return self._to_float(context.get(key), 0.0)
        if key == "trend_strength":
            trend = self._to_float(signal.get("trend", context.get("trend", 0.0)), 0.0)
            return min(1.0, abs(trend))
        if key == "momentum_strength":
            return min(1.0, abs(self._to_float(signal.get("momentum", context.get("momentum", 0.0)), 0.0)))
        if key == "volume_confirmation":
            v = self._to_float(signal.get("volume_spike", context.get("volume_spike", 0.0)), 0.0)
            return self._clip01(v if v <= 1.0 else v / 3.0)
        if key == "volatility_alignment":
            regime = str(signal.get("regime", context.get("regime", "RANGE_BOUND"))).upper()
            vol = self._to_float(signal.get("volatility", context.get("volatility", 0.0)), 0.0)
            if regime in {"LOW_VOLATILITY", "RANGE_BOUND"}:
                return self._clip01(1.0 - min(1.0, vol / 3.0))
            return self._clip01(min(1.0, vol / 2.0))
        if key == "liquidity_score":
            spread = self._to_float(signal.get("spread", context.get("spread", 0.0)), 0.0)
            if "liquidity_score" in context:
                return self._clip01(self._to_float(context.get("liquidity_score"), 0.0))
            if spread > 0:
                return self._clip01(1.0 - min(1.0, spread * 10.0))
            return 0.5
        return 0.0

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        keys = ["trend_strength", "momentum_strength", "volume_confirmation", "volatility_alignment", "liquidity_score"]
        cleaned = {k: max(0.0, float(weights.get(k, 0.0))) for k in keys}
        total = sum(cleaned.values())
        if total <= 1e-12:
            return {k: 1.0 / len(keys) for k in keys}
        return {k: cleaned[k] / total for k in keys}

    def _clip01(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _to_float(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

