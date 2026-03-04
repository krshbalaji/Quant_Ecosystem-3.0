"""Trend analysis primitives for regime detection."""

from __future__ import annotations

from typing import Dict, List, Tuple


class TrendAnalyzer:
    """Computes trend strength and direction from multi-series price data."""

    def __init__(self, ema_fast: int = 12, ema_slow: int = 26, adx_period: int = 14, momentum_lookback: int = 10):
        self.ema_fast = max(2, int(ema_fast))
        self.ema_slow = max(self.ema_fast + 1, int(ema_slow))
        self.adx_period = max(5, int(adx_period))
        self.momentum_lookback = max(2, int(momentum_lookback))

    def analyze(self, market_data: Dict) -> Dict:
        close = self._series(market_data, "close")
        high = self._series(market_data, "high", fallback=close)
        low = self._series(market_data, "low", fallback=close)
        if len(close) < self.ema_slow + 2:
            return {
                "trend_strength": 0.0,
                "trend_direction": "NEUTRAL",
                "ema_slope": 0.0,
                "adx_strength": 0.0,
                "price_momentum": 0.0,
            }

        ema_fast = self._ema(close, self.ema_fast)
        ema_slow = self._ema(close, self.ema_slow)
        ema_slope = self._ema_slope(ema_slow)
        adx = self._adx(high, low, close, self.adx_period)
        momentum = self._momentum(close, self.momentum_lookback)

        direction = "NEUTRAL"
        if ema_fast[-1] > ema_slow[-1] and momentum > 0:
            direction = "BULL"
        elif ema_fast[-1] < ema_slow[-1] and momentum < 0:
            direction = "BEAR"

        # Normalize to 0..100
        slope_score = min(100.0, abs(ema_slope) * 10000.0)
        adx_score = min(100.0, max(0.0, adx))
        momentum_score = min(100.0, abs(momentum) * 1000.0)
        strength = round((0.35 * slope_score) + (0.40 * adx_score) + (0.25 * momentum_score), 4)

        return {
            "trend_strength": strength,
            "trend_direction": direction,
            "ema_slope": round(ema_slope, 6),
            "adx_strength": round(adx, 4),
            "price_momentum": round(momentum, 6),
        }

    def _series(self, data: Dict, key: str, fallback: List[float] | None = None) -> List[float]:
        values = data.get(key, [])
        if isinstance(values, list) and values:
            return [float(v) for v in values]
        if fallback is not None:
            return list(fallback)
        return []

    def _ema(self, values: List[float], period: int) -> List[float]:
        alpha = 2.0 / (period + 1.0)
        out = [values[0]]
        for idx in range(1, len(values)):
            out.append(alpha * values[idx] + (1.0 - alpha) * out[-1])
        return out

    def _ema_slope(self, ema_values: List[float], lookback: int = 5) -> float:
        if len(ema_values) <= lookback:
            return 0.0
        start = ema_values[-lookback - 1]
        end = ema_values[-1]
        if start == 0:
            return 0.0
        return (end - start) / abs(start)

    def _momentum(self, close: List[float], lookback: int) -> float:
        if len(close) <= lookback:
            return 0.0
        start = close[-lookback - 1]
        end = close[-1]
        if start == 0:
            return 0.0
        return (end - start) / abs(start)

    def _adx(self, high: List[float], low: List[float], close: List[float], period: int) -> float:
        if min(len(high), len(low), len(close)) < period + 2:
            return 0.0

        tr = []
        plus_dm = []
        minus_dm = []
        for i in range(1, len(close)):
            tr_val = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
            up = high[i] - high[i - 1]
            down = low[i - 1] - low[i]
            plus = up if (up > down and up > 0) else 0.0
            minus = down if (down > up and down > 0) else 0.0
            tr.append(tr_val)
            plus_dm.append(plus)
            minus_dm.append(minus)

        atr = self._rma(tr, period)
        plus_di = []
        minus_di = []
        plus_sm = self._rma(plus_dm, period)
        minus_sm = self._rma(minus_dm, period)
        for idx in range(len(atr)):
            if atr[idx] == 0:
                plus_di.append(0.0)
                minus_di.append(0.0)
            else:
                plus_di.append(100.0 * (plus_sm[idx] / atr[idx]))
                minus_di.append(100.0 * (minus_sm[idx] / atr[idx]))

        dx = []
        for idx in range(len(plus_di)):
            den = plus_di[idx] + minus_di[idx]
            dx.append(0.0 if den == 0 else 100.0 * abs(plus_di[idx] - minus_di[idx]) / den)

        adx_series = self._rma(dx, period)
        return adx_series[-1] if adx_series else 0.0

    def _rma(self, values: List[float], period: int) -> List[float]:
        if not values:
            return []
        period = max(1, int(period))
        out = []
        seed_window = values[:period]
        seed = sum(seed_window) / len(seed_window)
        out.append(seed)
        alpha = 1.0 / period
        for i in range(period, len(values)):
            out.append((values[i] * alpha) + (out[-1] * (1.0 - alpha)))
        if len(out) < len(values):
            pad = [out[0]] * (len(values) - len(out))
            out = pad + out
        return out
