"""Volatility shift detection for early regime transitions."""

from __future__ import annotations

from typing import Dict, List


class VolatilityShiftDetector:
    """Detects volatility acceleration, ATR spikes, and range expansion."""

    def __init__(
        self,
        acceleration_threshold: float = 0.12,
        atr_spike_threshold: float = 1.25,
        range_expansion_threshold: float = 1.20,
    ):
        self.acceleration_threshold = max(0.0, float(acceleration_threshold))
        self.atr_spike_threshold = max(1.0, float(atr_spike_threshold))
        self.range_expansion_threshold = max(1.0, float(range_expansion_threshold))

    def detect(self, snapshot: Dict) -> Dict:
        """Return volatility shift diagnostics and normalized shift score."""
        close = [float(x) for x in snapshot.get("close", []) if self._is_num(x)]
        high = [float(x) for x in snapshot.get("high", []) if self._is_num(x)]
        low = [float(x) for x in snapshot.get("low", []) if self._is_num(x)]

        if len(close) < 35 or len(high) != len(close) or len(low) != len(close):
            return {
                "volatility_acceleration": 0.0,
                "atr_spike": 0.0,
                "range_expansion": 0.0,
                "vol_shift_score": 0.0,
            }

        vol_recent = self._realized_vol(close[-20:])
        vol_prev = self._realized_vol(close[-40:-20])
        vol_acc = 0.0
        if vol_prev > 1e-9:
            vol_acc = max(0.0, (vol_recent - vol_prev) / vol_prev)

        atr_recent = self._atr(high[-20:], low[-20:], close[-20:])
        atr_prev = self._atr(high[-40:-20], low[-40:-20], close[-40:-20])
        atr_spike = 0.0
        if atr_prev > 1e-9:
            atr_spike = max(0.0, atr_recent / atr_prev)

        range_recent = max(high[-20:]) - min(low[-20:])
        range_prev = max(high[-40:-20]) - min(low[-40:-20])
        range_expansion = 0.0
        if range_prev > 1e-9:
            range_expansion = max(0.0, range_recent / range_prev)

        acc_norm = min(1.0, vol_acc / max(self.acceleration_threshold, 1e-9))
        atr_norm = min(1.0, max(0.0, (atr_spike - 1.0) / (self.atr_spike_threshold - 1.0 + 1e-9)))
        range_norm = min(1.0, max(0.0, (range_expansion - 1.0) / (self.range_expansion_threshold - 1.0 + 1e-9)))
        shift_score = (0.45 * acc_norm) + (0.35 * atr_norm) + (0.20 * range_norm)

        return {
            "volatility_acceleration": round(vol_acc, 6),
            "atr_spike": round(atr_spike, 6),
            "range_expansion": round(range_expansion, 6),
            "vol_shift_score": round(min(1.0, max(0.0, shift_score)), 6),
        }

    def _realized_vol(self, close: List[float]) -> float:
        if len(close) < 3:
            return 0.0
        rets = []
        for i in range(1, len(close)):
            prev = close[i - 1]
            if abs(prev) <= 1e-12:
                continue
            rets.append((close[i] - prev) / prev)
        if not rets:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / len(rets)
        return var ** 0.5

    def _atr(self, high: List[float], low: List[float], close: List[float]) -> float:
        if len(close) < 2:
            return 0.0
        trs = []
        for i in range(1, len(close)):
            prev_close = close[i - 1]
            tr = max(high[i] - low[i], abs(high[i] - prev_close), abs(low[i] - prev_close))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else 0.0

    def _is_num(self, value) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

