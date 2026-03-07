"""Volatility monitor for market pulse."""

from __future__ import annotations

from typing import Dict, List


class VolatilityMonitor:
    """Detects sudden volatility expansion using ATR-like behavior."""

    def __init__(self, atr_multiplier: float = 1.5, **kwargs):
        self.atr_multiplier = max(1.1, float(atr_multiplier))

    def evaluate(self, snapshot: Dict) -> Dict:
        high = self._series(snapshot.get("high", []))
        low = self._series(snapshot.get("low", []))
        close = self._series(snapshot.get("close", []))
        if len(close) < 30 or len(high) != len(close) or len(low) != len(close):
            return {"triggered": False, "event_type": "VOLATILITY_SPIKE", "strength": 0.0}

        atr_curr = self._atr(high[-14:], low[-14:], close[-14:])
        atr_hist = []
        for i in range(14, len(close) - 1):
            atr_hist.append(self._atr(high[i - 14 : i], low[i - 14 : i], close[i - 14 : i]))
        atr_mean = sum(atr_hist) / max(1, len(atr_hist))

        triggered = atr_mean > 1e-9 and atr_curr > (atr_mean * self.atr_multiplier)
        strength = 0.0
        if atr_mean > 1e-9:
            strength = min(1.0, max(0.0, (atr_curr / atr_mean - 1.0)))
        return {
            "triggered": bool(triggered),
            "event_type": "VOLATILITY_SPIKE",
            "strength": round(strength, 6),
            "atr_current": round(atr_curr, 8),
            "atr_mean": round(atr_mean, 8),
        }

    def _atr(self, high: List[float], low: List[float], close: List[float]) -> float:
        if len(close) < 2:
            return 0.0
        tr = []
        for i in range(1, len(close)):
            prev = close[i - 1]
            tr.append(max(high[i] - low[i], abs(high[i] - prev), abs(low[i] - prev)))
        return sum(tr) / len(tr) if tr else 0.0

    def _series(self, values) -> List[float]:
        out = []
        for v in values or []:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                continue
        return out

