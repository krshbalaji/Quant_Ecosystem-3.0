"""Signal detection engine for global alpha opportunities."""

from __future__ import annotations

from typing import Dict, List


class SignalDetector:
    """Detects alpha patterns across OHLCV snapshots."""

    def detect(self, snapshot: Dict) -> List[Dict]:
        close = list(snapshot.get("close", []))
        high = list(snapshot.get("high", []))
        low = list(snapshot.get("low", []))
        volume = list(snapshot.get("volume", []))
        if len(close) < 30:
            return []

        signals = []
        rsi = self._rsi(close, 14)
        macd, macd_signal = self._macd(close)
        vwap = self._vwap(close, volume)
        bb_upper, bb_lower = self._bollinger(close, 20, 2.0)
        atr = self._atr(high, low, close, 14)
        vol_z = self._zscore(volume[-1], volume[-30:])
        trend_accel = self._trend_acceleration(close)

        # Momentum breakout
        if close[-1] > bb_upper and macd > macd_signal:
            strength = self._clamp(0.5 + abs(macd - macd_signal) * 10.0 + max(0.0, vol_z) * 0.1)
            signals.append(self._signal(snapshot, "momentum_breakout", strength))

        # Mean reversion
        if (close[-1] < bb_lower and rsi < 35) or (close[-1] > bb_upper and rsi > 65):
            strength = self._clamp(0.45 + abs(50 - rsi) / 100.0)
            signals.append(self._signal(snapshot, "mean_reversion_signal", strength))

        # Volatility expansion
        if atr > 0 and (high[-1] - low[-1]) > atr * 1.2:
            strength = self._clamp(0.4 + ((high[-1] - low[-1]) / max(atr, 1e-9)) * 0.1)
            signals.append(self._signal(snapshot, "volatility_expansion", strength))

        # Volume spike
        if vol_z > 1.5:
            strength = self._clamp(0.4 + min(vol_z, 5.0) * 0.12)
            signals.append(self._signal(snapshot, "volume_spike", strength))

        # Trend acceleration
        if abs(trend_accel) > 0.001 and ((trend_accel > 0 and close[-1] > vwap) or (trend_accel < 0 and close[-1] < vwap)):
            strength = self._clamp(0.35 + min(abs(trend_accel) * 200.0, 0.65))
            signals.append(self._signal(snapshot, "trend_acceleration", strength))

        # Range compression breakout
        if self._range_compression(close[:-1]) and (close[-1] > max(close[-10:]) or close[-1] < min(close[-10:])):
            signals.append(self._signal(snapshot, "range_compression_breakout", 0.62))

        return signals

    def _signal(self, snapshot: Dict, signal_type: str, strength: float) -> Dict:
        return {
            "symbol": snapshot.get("symbol"),
            "asset_class": snapshot.get("asset_class", "stocks"),
            "signal_type": signal_type,
            "signal_strength": round(self._clamp(strength), 4),
            "timeframe": "5m",
            "volatility": float(snapshot.get("volatility", 0.0)),
            "spread": float((snapshot.get("spread") or [0.0])[-1]),
            "liquidity_score": float(snapshot.get("depth_score", 0.5)),
            "trend_quality": round(abs(self._trend_acceleration(snapshot.get("close", []))) * 100.0, 4),
        }

    def _rsi(self, close: List[float], period: int) -> float:
        gains = []
        losses = []
        start = max(1, len(close) - period)
        for i in range(start, len(close)):
            delta = close[i] - close[i - 1]
            gains.append(max(0.0, delta))
            losses.append(max(0.0, -delta))
        avg_gain = sum(gains) / max(1, len(gains))
        avg_loss = sum(losses) / max(1, len(losses))
        if avg_loss <= 1e-9:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _macd(self, close: List[float]) -> tuple[float, float]:
        fast = self._ema(close, 12)
        slow = self._ema(close, 26)
        series = [f - s for f, s in zip(fast[-len(slow):], slow)]
        signal = self._ema(series, 9)
        return series[-1], signal[-1] if signal else 0.0

    def _vwap(self, close: List[float], volume: List[float]) -> float:
        if not close or not volume:
            return 0.0
        n = min(len(close), len(volume))
        c = close[-n:]
        v = volume[-n:]
        den = sum(v)
        if den <= 1e-9:
            return c[-1]
        return sum(c[i] * v[i] for i in range(n)) / den

    def _bollinger(self, close: List[float], period: int, mult: float) -> tuple[float, float]:
        sample = close[-period:]
        mean = sum(sample) / len(sample)
        var = sum((x - mean) ** 2 for x in sample) / len(sample)
        std = var ** 0.5
        return mean + (std * mult), mean - (std * mult)

    def _atr(self, high: List[float], low: List[float], close: List[float], period: int) -> float:
        if len(close) < period + 1:
            return 0.0
        trs = []
        start = len(close) - period
        for i in range(start, len(close)):
            prev_close = close[i - 1]
            tr = max(high[i] - low[i], abs(high[i] - prev_close), abs(low[i] - prev_close))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else 0.0

    def _ema(self, data: List[float], period: int) -> List[float]:
        if not data:
            return []
        alpha = 2.0 / (period + 1.0)
        out = [data[0]]
        for i in range(1, len(data)):
            out.append(alpha * data[i] + (1.0 - alpha) * out[-1])
        return out

    def _zscore(self, value: float, sample: List[float]) -> float:
        if len(sample) < 2:
            return 0.0
        mean = sum(sample) / len(sample)
        var = sum((x - mean) ** 2 for x in sample) / max(1, len(sample) - 1)
        std = var ** 0.5
        if std <= 1e-9:
            return 0.0
        return (value - mean) / std

    def _trend_acceleration(self, close: List[float]) -> float:
        if len(close) < 20:
            return 0.0
        short = (close[-1] - close[-5]) / max(close[-5], 1e-9)
        long = (close[-6] - close[-10]) / max(close[-10], 1e-9)
        return short - long

    def _range_compression(self, close: List[float]) -> bool:
        if len(close) < 20:
            return False
        recent = close[-10:]
        prev = close[-20:-10]
        recent_range = max(recent) - min(recent)
        prev_range = max(prev) - min(prev)
        return recent_range < (prev_range * 0.7)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

