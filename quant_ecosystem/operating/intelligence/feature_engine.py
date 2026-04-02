from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np


class FeatureEngine:
    """
    Reusable indicator computation layer built on top of MarketDataEngine.

    This engine is intentionally lightweight and stateless between calls
    beyond basic per-session caching.
    """

    def __init__(self, market_data_engine, **kwargs):
        self.market_data = market_data_engine

    # --- Low-level helpers -------------------------------------------------

    def get_close_series(self, symbol: str, timeframe: str = "5m", lookback: int = 200) -> List[float]:
        series = self.market_data.get_series(symbol=symbol, timeframe=timeframe, lookback=lookback)
        return [float(x) for x in series or []]

    def get_volume_series(self, symbol: str, timeframe: str = "5m", lookback: int = 200) -> List[float]:
        snap = self.market_data.get_snapshot(symbol=symbol, lookback=lookback)
        vols = list((snap or {}).get("volume") or [])
        return [float(x) for x in vols]

    # --- Core indicators ---------------------------------------------------

    def get_rsi(self, symbol: str, timeframe: str = "5m", length: int = 14) -> Optional[float]:
        closes = self.get_close_series(symbol, timeframe=timeframe, lookback=length + 5)
        if len(closes) < length + 1:
            return None
        arr = np.array(closes, dtype=float)
        delta = np.diff(arr)
        gains = np.clip(delta, 0.0, None)
        losses = np.clip(-delta, 0.0, None)
        if len(gains) < length:
            return None
        avg_gain = gains[-length:].mean()
        avg_loss = losses[-length:].mean()
        if avg_loss == 0:
            rs = 10.0
        else:
            rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return float(rsi)

    def get_atr(self, symbol: str, timeframe: str = "5m", length: int = 14) -> Optional[float]:
        snap = self.market_data.get_snapshot(symbol=symbol, lookback=length + 5)
        highs = np.array(list((snap or {}).get("high") or []), dtype=float)
        lows = np.array(list((snap or {}).get("low") or []), dtype=float)
        closes = np.array(list((snap or {}).get("close") or []), dtype=float)
        if len(highs) < length + 1 or len(lows) < length + 1 or len(closes) < length + 1:
            return None
        prev_close = np.roll(closes, 1)
        prev_close[0] = closes[0]
        tr1 = highs - lows
        tr2 = np.abs(highs - prev_close)
        tr3 = np.abs(lows - prev_close)
        tr = np.maximum.reduce([tr1, tr2, tr3])
        atr = tr[-length:].mean()
        return float(atr)

    def get_vwap(self, symbol: str, timeframe: str = "5m", lookback: int = 30) -> Optional[float]:
        snap = self.market_data.get_snapshot(symbol=symbol, lookback=lookback)
        closes = np.array(list((snap or {}).get("close") or []), dtype=float)
        vols = np.array(list((snap or {}).get("volume") or []), dtype=float)
        if len(closes) == 0 or len(vols) == 0:
            return None
        notional = (closes * vols).sum()
        vol_sum = vols.sum()
        if vol_sum == 0:
            return None
        return float(notional / vol_sum)

    def get_momentum(self, symbol: str, timeframe: str = "5m", lookback: int = 20) -> Optional[float]:
        closes = self.get_close_series(symbol, timeframe=timeframe, lookback=lookback + 1)
        if len(closes) < lookback + 1:
            return None
        start = float(closes[-(lookback + 1)])
        end = float(closes[-1])
        if start == 0:
            return None
        return float((end - start) / abs(start))

    def get_volatility(self, symbol: str, timeframe: str = "5m", lookback: int = 40) -> Optional[float]:
        closes = self.get_close_series(symbol, timeframe=timeframe, lookback=lookback + 1)
        if len(closes) < lookback + 1:
            return None
        arr = np.array(closes, dtype=float)
        rets = np.diff(arr) / np.where(arr[:-1] == 0, 1.0, arr[:-1])
        return float(np.std(rets[-lookback:]))

    def get_volume_spike_score(self, symbol: str, timeframe: str = "5m", lookback: int = 30) -> Optional[float]:
        vols = self.get_volume_series(symbol, timeframe=timeframe, lookback=lookback + 1)
        if len(vols) < lookback + 1:
            return None
        arr = np.array(vols, dtype=float)
        base = arr[-(lookback + 1) : -1]
        current = arr[-1]
        mean = base.mean()
        if mean <= 0:
            return None
        return float(current / mean)

    # Hook for orchestrator refresh if needed later
    def refresh(self) -> None:
        """
        Placeholder for future stateful caching. No-op for now.
        """
        return None

