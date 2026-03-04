"""Feature engineering for adaptive regime detection."""

from __future__ import annotations

from typing import Dict, List, Tuple


class FeatureEngineer:
    """Builds normalized feature vectors from market snapshots."""

    FEATURE_ORDER = [
        "ret_1",
        "ret_5",
        "rolling_vol",
        "atr",
        "rsi",
        "macd",
        "trend_slope",
        "volume_spike",
        "vol_percentile",
        "range_compression",
        "market_breadth",
        "vix_norm",
    ]

    def build_feature_vector(self, snapshot: Dict, extra_signals: Dict | None = None) -> Dict:
        """Create feature dictionary from OHLCV + auxiliary signals."""
        extra = extra_signals or {}
        close = list(snapshot.get("close", []))
        high = list(snapshot.get("high", []))
        low = list(snapshot.get("low", []))
        volume = list(snapshot.get("volume", []))
        if len(close) < 30:
            return {name: 0.0 for name in self.FEATURE_ORDER}

        ret_1 = self._ret(close, 1)
        ret_5 = self._ret(close, 5)
        rolling_vol = self._rolling_vol(close)
        atr = self._atr(high, low, close, 14)
        rsi = self._rsi(close, 14)
        macd = self._macd(close)
        trend_slope = self._trend_slope(close, 20)
        volume_spike = self._volume_spike(volume, 30)
        vol_percentile = self._vol_percentile(rolling_vol)
        range_compression = self._range_compression(close, 20, 10)
        market_breadth = self._clip(self._safe_float(extra.get("market_breadth"), 0.0), -1.0, 1.0)
        vix_norm = self._clip(self._safe_float(extra.get("vix"), 18.0) / 40.0, 0.0, 2.0)

        return {
            "ret_1": ret_1,
            "ret_5": ret_5,
            "rolling_vol": rolling_vol,
            "atr": atr,
            "rsi": rsi,
            "macd": macd,
            "trend_slope": trend_slope,
            "volume_spike": volume_spike,
            "vol_percentile": vol_percentile,
            "range_compression": range_compression,
            "market_breadth": market_breadth,
            "vix_norm": vix_norm,
        }

    def normalize_features(self, features: Dict) -> Dict:
        """Normalize feature dictionary into bounded ranges."""
        return {
            "ret_1": self._clip(float(features.get("ret_1", 0.0)) * 10.0, -1.0, 1.0),
            "ret_5": self._clip(float(features.get("ret_5", 0.0)) * 10.0, -1.0, 1.0),
            "rolling_vol": self._clip(float(features.get("rolling_vol", 0.0)) / 5.0, 0.0, 1.0),
            "atr": self._clip(float(features.get("atr", 0.0)) / 5.0, 0.0, 1.0),
            "rsi": self._clip((float(features.get("rsi", 50.0)) - 50.0) / 50.0, -1.0, 1.0),
            "macd": self._clip(float(features.get("macd", 0.0)) * 20.0, -1.0, 1.0),
            "trend_slope": self._clip(float(features.get("trend_slope", 0.0)) * 100.0, -1.0, 1.0),
            "volume_spike": self._clip(float(features.get("volume_spike", 0.0)) / 3.0, 0.0, 1.0),
            "vol_percentile": self._clip(float(features.get("vol_percentile", 0.0)), 0.0, 1.0),
            "range_compression": self._clip(float(features.get("range_compression", 0.0)), 0.0, 1.0),
            "market_breadth": self._clip(float(features.get("market_breadth", 0.0)), -1.0, 1.0),
            "vix_norm": self._clip(float(features.get("vix_norm", 0.45)), 0.0, 1.0),
        }

    def as_ordered_vector(self, normalized_features: Dict) -> List[float]:
        """Return features in stable order for model prediction."""
        return [float(normalized_features.get(name, 0.0)) for name in self.FEATURE_ORDER]

    def _ret(self, close: List[float], periods: int) -> float:
        if len(close) <= periods or close[-periods - 1] == 0:
            return 0.0
        return (close[-1] - close[-periods - 1]) / close[-periods - 1]

    def _rolling_vol(self, close: List[float], window: int = 20) -> float:
        sample = close[-window:]
        rets = []
        for i in range(1, len(sample)):
            prev = sample[i - 1]
            if prev == 0:
                continue
            rets.append((sample[i] - prev) / prev)
        if not rets:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / len(rets)
        return (var ** 0.5) * 100.0

    def _atr(self, high: List[float], low: List[float], close: List[float], period: int) -> float:
        if len(close) < period + 1:
            return 0.0
        trs = []
        start = len(close) - period
        for i in range(start, len(close)):
            prev = close[i - 1]
            tr = max(high[i] - low[i], abs(high[i] - prev), abs(low[i] - prev))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else 0.0

    def _rsi(self, close: List[float], period: int) -> float:
        gains = []
        losses = []
        start = max(1, len(close) - period)
        for i in range(start, len(close)):
            d = close[i] - close[i - 1]
            gains.append(max(0.0, d))
            losses.append(max(0.0, -d))
        avg_gain = sum(gains) / max(1, len(gains))
        avg_loss = sum(losses) / max(1, len(losses))
        if avg_loss <= 1e-9:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _macd(self, close: List[float]) -> float:
        ema12 = self._ema(close, 12)
        ema26 = self._ema(close, 26)
        if not ema12 or not ema26:
            return 0.0
        return ema12[-1] - ema26[-1]

    def _ema(self, series: List[float], period: int) -> List[float]:
        if not series:
            return []
        alpha = 2.0 / (period + 1.0)
        out = [series[0]]
        for i in range(1, len(series)):
            out.append(alpha * series[i] + (1.0 - alpha) * out[-1])
        return out

    def _trend_slope(self, close: List[float], window: int) -> float:
        if len(close) < window:
            return 0.0
        y = close[-window:]
        x = list(range(window))
        x_mean = sum(x) / window
        y_mean = sum(y) / window
        num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(window))
        den = sum((x[i] - x_mean) ** 2 for i in range(window))
        if den <= 1e-9 or y_mean == 0:
            return 0.0
        return (num / den) / y_mean

    def _volume_spike(self, volume: List[float], window: int) -> float:
        if len(volume) < window:
            return 0.0
        sample = volume[-window:]
        mean = sum(sample) / window
        var = sum((v - mean) ** 2 for v in sample) / max(1, window - 1)
        std = var ** 0.5
        if std <= 1e-9:
            return 0.0
        return (sample[-1] - mean) / std

    def _vol_percentile(self, rolling_vol: float) -> float:
        # Smooth approximation for percentile mapping.
        return self._clip(rolling_vol / 2.0, 0.0, 1.0)

    def _range_compression(self, close: List[float], prev_window: int, recent_window: int) -> float:
        if len(close) < prev_window + recent_window:
            return 0.0
        prev = close[-(prev_window + recent_window):-recent_window]
        recent = close[-recent_window:]
        prev_range = max(prev) - min(prev)
        recent_range = max(recent) - min(recent)
        if prev_range <= 1e-9:
            return 0.0
        compression = 1.0 - (recent_range / prev_range)
        return self._clip(compression, 0.0, 1.0)

    def _clip(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _safe_float(self, value, default: float = 0.0) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)
