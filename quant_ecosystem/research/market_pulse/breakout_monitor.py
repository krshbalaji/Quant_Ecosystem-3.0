"""Breakout monitor for market pulse."""

from __future__ import annotations

from typing import Dict, List


class BreakoutMonitor:
    """Detects price escaping a recent range and trend slope shifts."""

    def __init__(self, range_window: int = 20, trend_shift_threshold: float = 0.20, **kwargs):
        self.range_window = max(10, int(range_window))
        self.trend_shift_threshold = max(0.05, float(trend_shift_threshold))

    def evaluate(self, snapshot: Dict) -> Dict:
        close = self._series(snapshot.get("close", []))
        if len(close) < self.range_window + 10:
            return {"triggered": False, "event_type": "PRICE_BREAKOUT", "strength": 0.0}

        last = close[-1]
        window = close[-self.range_window - 1 : -1]
        high = max(window)
        low = min(window)

        up_break = last > high
        down_break = last < low
        breakout_strength = 0.0
        if high > low:
            if up_break:
                breakout_strength = min(1.0, (last - high) / (high - low))
            elif down_break:
                breakout_strength = min(1.0, (low - last) / (high - low))

        slope_recent = self._slope(close[-20:])
        slope_prev = self._slope(close[-40:-20]) if len(close) >= 40 else slope_recent
        slope_shift = abs(slope_recent - slope_prev)
        trend_shift_triggered = slope_shift >= self.trend_shift_threshold
        trend_shift_strength = min(1.0, slope_shift / max(self.trend_shift_threshold, 1e-9))

        event_type = "PRICE_BREAKOUT"
        triggered = up_break or down_break
        if trend_shift_triggered and trend_shift_strength > breakout_strength:
            event_type = "TREND_SHIFT"
            triggered = True

        return {
            "triggered": bool(triggered),
            "event_type": event_type,
            "direction": "UP" if up_break else ("DOWN" if down_break else "FLAT"),
            "strength": round(max(breakout_strength, trend_shift_strength if trend_shift_triggered else 0.0), 6),
            "slope_shift": round(slope_shift, 6),
        }

    def _slope(self, series: List[float]) -> float:
        n = len(series)
        if n < 2:
            return 0.0
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(series) / n
        num = sum((x[i] - x_mean) * (series[i] - y_mean) for i in range(n))
        den = sum((x[i] - x_mean) ** 2 for i in range(n))
        if den <= 1e-12 or abs(y_mean) <= 1e-12:
            return 0.0
        return (num / den) / y_mean

    def _series(self, values) -> List[float]:
        out = []
        for v in values or []:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                continue
        return out

