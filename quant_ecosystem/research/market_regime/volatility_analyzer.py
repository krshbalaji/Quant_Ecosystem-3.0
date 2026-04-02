"""Volatility analysis module for market regime detection."""

from __future__ import annotations

from collections import deque
from math import log, sqrt
from typing import Deque, Dict, List


class VolatilityAnalyzer:
    """Computes ATR/realized volatility and percentile state."""

    def __init__(self, atr_period: int = 14, percentile_window: int = 200, **kwargs):
        self.atr_period = max(5, int(atr_period))
        self.percentile_window = max(50, int(percentile_window))
        self._history: Deque[float] = deque(maxlen=self.percentile_window)

    def analyze(self, market_data: Dict) -> Dict:
        close = self._series(market_data, "close")
        high = self._series(market_data, "high", fallback=close)
        low = self._series(market_data, "low", fallback=close)

        atr = self._atr(high, low, close, self.atr_period)
        realized = self._realized_vol(close)
        current = max(atr, realized)
        if current > 0:
            self._history.append(current)

        percentile = self._percentile(current)
        if percentile >= 90:
            state = "HIGH"
        elif percentile <= 25:
            state = "LOW"
        else:
            state = "NORMAL"

        return {
            "atr_volatility": round(atr, 6),
            "realized_volatility": round(realized, 6),
            "volatility_percentile": round(percentile, 4),
            "volatility_state": state,
        }

    def _series(self, data: Dict, key: str, fallback: List[float] | None = None) -> List[float]:
        values = data.get(key, [])
        if isinstance(values, list) and values:
            return [float(v) for v in values]
        if fallback is not None:
            return list(fallback)
        return []

    def _atr(self, high: List[float], low: List[float], close: List[float], period: int) -> float:
        if min(len(high), len(low), len(close)) < period + 2:
            return 0.0
        tr = []
        for i in range(1, len(close)):
            tr.append(max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])))
        recent = tr[-period:]
        base = close[-1] if close[-1] else 1.0
        return (sum(recent) / len(recent)) / abs(base)

    def _realized_vol(self, close: List[float], lookback: int = 30) -> float:
        if len(close) < lookback + 2:
            return 0.0
        rets = []
        sample = close[-(lookback + 1):]
        for i in range(1, len(sample)):
            prev = sample[i - 1]
            cur = sample[i]
            if prev <= 0 or cur <= 0:
                continue
            rets.append(log(cur / prev))
        if len(rets) < 2:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
        return sqrt(max(var, 0.0)) * sqrt(252)

    def _percentile(self, value: float) -> float:
        if len(self._history) < 30:
            return 50.0
        hist = sorted(self._history)
        less_equal = len([x for x in hist if x <= value])
        return 100.0 * (less_equal / len(hist))
