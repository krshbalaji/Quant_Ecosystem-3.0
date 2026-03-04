"""Trend shift detection for early transition signaling."""

from __future__ import annotations

from typing import Dict, List


class TrendShiftDetector:
    """Detects slope change, MA curvature, and momentum divergence."""

    def __init__(
        self,
        slope_change_threshold: float = 0.20,
        curvature_threshold: float = 0.0015,
        divergence_threshold: float = 0.010,
    ):
        self.slope_change_threshold = max(0.0, float(slope_change_threshold))
        self.curvature_threshold = max(0.0, float(curvature_threshold))
        self.divergence_threshold = max(0.0, float(divergence_threshold))

    def detect(self, snapshot: Dict) -> Dict:
        """Return trend shift diagnostics and normalized trend shift score."""
        close = [float(x) for x in snapshot.get("close", []) if self._is_num(x)]
        if len(close) < 45:
            return {
                "trend_shift": 0.0,
                "slope_change": 0.0,
                "ma_curvature": 0.0,
                "momentum_divergence": 0.0,
                "reversal_risk": 0.0,
            }

        slope_recent = self._slope(close[-20:])
        slope_prev = self._slope(close[-40:-20])
        slope_change = abs(slope_recent - slope_prev)

        fast_ma = self._ema(close, 8)
        mid_ma = self._ema(close, 21)
        slow_ma = self._ema(close, 34)
        # Curvature proxy: second derivative-like shift in MA spread.
        spread_now = (fast_ma[-1] - mid_ma[-1]) - (mid_ma[-1] - slow_ma[-1])
        spread_prev = (fast_ma[-6] - mid_ma[-6]) - (mid_ma[-6] - slow_ma[-6])
        ma_curvature = abs(spread_now - spread_prev)

        price_mom = self._momentum(close, 12)
        ma_mom = self._momentum(mid_ma, 12)
        momentum_divergence = abs(price_mom - ma_mom)

        # Direction flip risk: sign change of slope.
        sign_flip = 1.0 if (slope_recent * slope_prev) < 0 else 0.0
        reversal_risk = min(1.0, (sign_flip * 0.5) + min(0.5, momentum_divergence * 10.0))

        slope_norm = min(1.0, slope_change / max(self.slope_change_threshold, 1e-9))
        curv_norm = min(1.0, ma_curvature / max(self.curvature_threshold, 1e-9))
        div_norm = min(1.0, momentum_divergence / max(self.divergence_threshold, 1e-9))
        trend_shift = (0.40 * slope_norm) + (0.30 * curv_norm) + (0.30 * div_norm)

        return {
            "trend_shift": round(min(1.0, max(0.0, trend_shift)), 6),
            "slope_change": round(slope_change, 6),
            "ma_curvature": round(ma_curvature, 6),
            "momentum_divergence": round(momentum_divergence, 6),
            "reversal_risk": round(reversal_risk, 6),
            "trend_direction_recent": "UP" if slope_recent > 0 else ("DOWN" if slope_recent < 0 else "FLAT"),
        }

    def _ema(self, series: List[float], period: int) -> List[float]:
        if not series:
            return []
        alpha = 2.0 / (period + 1.0)
        out = [series[0]]
        for i in range(1, len(series)):
            out.append(alpha * series[i] + (1.0 - alpha) * out[-1])
        return out

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

    def _momentum(self, series: List[float], lookback: int) -> float:
        if len(series) <= lookback:
            return 0.0
        base = series[-lookback - 1]
        if abs(base) <= 1e-12:
            return 0.0
        return (series[-1] - base) / base

    def _is_num(self, value) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

