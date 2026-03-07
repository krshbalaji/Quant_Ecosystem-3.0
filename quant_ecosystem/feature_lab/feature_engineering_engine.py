"""
feature_engineering_engine.py
Orchestrates full feature computation per symbol across multiple timeframes.
Reads raw OHLCV from MarketDataEngine, writes features to FeatureStore.
Designed for parallel execution via Ray.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from quant_ecosystem.feature_lab.feature_store import FeatureStore
from quant_ecosystem.feature_lab import indicator_library as ind


# Default feature set computed for every symbol × timeframe
_DEFAULT_FEATURE_GROUPS: List[str] = [
    "trend",
    "momentum",
    "volatility",
    "volume",
    "statistical",
]


class SymbolFeatureSet:
    """Holds computed features for one symbol at one point in time."""

    __slots__ = ["symbol", "timeframe", "timestamp", "features", "computed_at"]

    def __init__(self, symbol: str, timeframe: str, timestamp: int,
                 features: Dict[str, float], **kwargs) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.timestamp = timestamp
        self.features = features
        self.computed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "features": self.features,
            "computed_at": self.computed_at,
        }


class FeatureEngineeringEngine:
    """
    Institutional feature pipeline.
    
    For each (symbol, timeframe), extracts OHLCV from market data,
    computes the full indicator suite, and persists to FeatureStore.
    
    Integration:
        engine = FeatureEngineeringEngine(market_data_engine=market_data)
        snapshot = engine.compute(symbol="NSE:SBIN-EQ", timeframe="5m")
        features = snapshot.features  # Dict[str, float]
    """

    def __init__(
        self,
        market_data_engine: Any,
        feature_store: Optional[FeatureStore] = None,
        timeframes: Optional[List[str]] = None,
        feature_groups: Optional[List[str]] = None,
        lookback: int = 250, **kwargs
    ) -> None:
        self.market_data = market_data_engine
        self.store = feature_store or FeatureStore()
        self.timeframes = timeframes or ["5m", "15m", "1h", "1d"]
        self.feature_groups = set(feature_groups or _DEFAULT_FEATURE_GROUPS)
        self.lookback = lookback
        self._cache: Dict[str, SymbolFeatureSet] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(self, symbol: str, timeframe: str = "5m",
                persist: bool = True) -> Optional[SymbolFeatureSet]:
        """Compute all features for one symbol/timeframe pair."""
        ohlcv = self._fetch_ohlcv(symbol, timeframe)
        if ohlcv is None:
            return None

        close = ohlcv["close"]
        high = ohlcv["high"]
        low = ohlcv["low"]
        volume = ohlcv["volume"]
        timestamp = ohlcv["timestamp"]

        features: Dict[str, float] = {}

        if "trend" in self.feature_groups:
            features.update(self._compute_trend(close, high, low))

        if "momentum" in self.feature_groups:
            features.update(self._compute_momentum(close, high, low))

        if "volatility" in self.feature_groups:
            features.update(self._compute_volatility(close, high, low))

        if "volume" in self.feature_groups and volume is not None:
            features.update(self._compute_volume(close, high, low, volume))

        if "statistical" in self.feature_groups:
            features.update(self._compute_statistical(close))

        # Sanitize: replace inf/nan with 0
        features = {k: float(v) if np.isfinite(v) else 0.0
                    for k, v in features.items()}

        snapshot = SymbolFeatureSet(symbol, timeframe, timestamp, features)
        self._cache[f"{symbol}|{timeframe}"] = snapshot

        if persist:
            self.store.write_snapshot(symbol, timeframe, timestamp, features)

        return snapshot

    def compute_all(self, symbols: List[str], timeframe: str = "5m",
                    persist: bool = True) -> List[SymbolFeatureSet]:
        """Compute features for a list of symbols sequentially."""
        results = []
        for sym in symbols:
            snap = self.compute(sym, timeframe, persist=persist)
            if snap is not None:
                results.append(snap)
        return results

    def compute_all_timeframes(self, symbol: str,
                                persist: bool = True) -> Dict[str, SymbolFeatureSet]:
        """Compute all timeframes for a single symbol."""
        return {
            tf: snap
            for tf in self.timeframes
            for snap in [self.compute(symbol, tf, persist=persist)]
            if snap is not None
        }

    def get_cached(self, symbol: str, timeframe: str) -> Optional[SymbolFeatureSet]:
        return self._cache.get(f"{symbol}|{timeframe}")

    def refresh(self, symbols: Optional[List[str]] = None,
                timeframe: str = "5m") -> None:
        """Refresh hook called by orchestrator each cycle."""
        if symbols:
            self.compute_all(symbols, timeframe)

    # ------------------------------------------------------------------
    # OHLCV fetch
    # ------------------------------------------------------------------

    def _fetch_ohlcv(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        try:
            snap = self.market_data.get_snapshot(symbol=symbol, lookback=self.lookback)
            if not snap:
                return None
            closes = snap.get("close") or []
            highs = snap.get("high") or []
            lows = snap.get("low") or []
            volumes = snap.get("volume") or []
            if len(closes) < 30:
                return None
            return {
                "close": np.array(closes, dtype=np.float64),
                "high": np.array(highs or closes, dtype=np.float64),
                "low": np.array(lows or closes, dtype=np.float64),
                "volume": np.array(volumes, dtype=np.float64) if volumes else None,
                "timestamp": int(time.time()),
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Feature groups
    # ------------------------------------------------------------------

    def _compute_trend(self, close: np.ndarray, high: np.ndarray,
                       low: np.ndarray) -> Dict[str, float]:
        out: Dict[str, float] = {}
        try:
            e9 = ind.ema(close, 9)
            e21 = ind.ema(close, 21)
            e50 = ind.ema(close, 50)
            e200 = ind.ema(close, 200)
            s20 = ind.sma(close, 20)
            s50 = ind.sma(close, 50)

            last = close[-1]
            out["ema_9"] = float(e9[-1]) if not np.isnan(e9[-1]) else 0.0
            out["ema_21"] = float(e21[-1]) if not np.isnan(e21[-1]) else 0.0
            out["ema_50"] = float(e50[-1]) if not np.isnan(e50[-1]) else 0.0
            out["ema_200"] = float(e200[-1]) if not np.isnan(e200[-1]) else 0.0
            out["sma_20"] = float(s20[-1]) if not np.isnan(s20[-1]) else 0.0
            out["sma_50"] = float(s50[-1]) if not np.isnan(s50[-1]) else 0.0

            # Distance from MAs (normalized)
            for name, val in [("ema_9", out["ema_9"]), ("ema_21", out["ema_21"]),
                               ("ema_50", out["ema_50"]), ("ema_200", out["ema_200"])]:
                out[f"price_vs_{name}_pct"] = (last - val) / val * 100.0 if val != 0 else 0.0

            # MA slopes (1-bar change)
            for name, arr in [("ema_9", e9), ("ema_21", e21), ("ema_50", e50)]:
                if len(arr) >= 2 and not np.isnan(arr[-2]):
                    out[f"{name}_slope_pct"] = (arr[-1] - arr[-2]) / arr[-2] * 100.0 if arr[-2] != 0 else 0.0
                else:
                    out[f"{name}_slope_pct"] = 0.0

            # Trend alignment
            out["trend_alignment"] = float(
                (1 if out["ema_9"] > out["ema_21"] else -1) +
                (1 if out["ema_21"] > out["ema_50"] else -1) +
                (1 if out["ema_50"] > out["ema_200"] else -1)
            ) / 3.0

            # Donchian breakout position
            if len(close) >= 20:
                _, _, dc_lower = ind.donchian(high, low, 20)
                dc_upper, _, _ = ind.donchian(high, low, 20)
                dc_range = float(dc_upper[-1] - dc_lower[-1])
                out["donchian_position_20"] = (
                    (last - float(dc_lower[-1])) / dc_range if dc_range > 0 else 0.5
                )

            # HMA direction
            if len(close) >= 16:
                h = ind.hma(close, 16)
                out["hma_16_direction"] = 1.0 if (not np.isnan(h[-1]) and not np.isnan(h[-2])
                                                   and h[-1] > h[-2]) else -1.0

        except Exception:
            pass
        return out

    def _compute_momentum(self, close: np.ndarray, high: np.ndarray,
                           low: np.ndarray) -> Dict[str, float]:
        out: Dict[str, float] = {}
        try:
            out["rsi_14"] = float(ind.rsi(close, 14)[-1]) if len(close) > 14 else 50.0
            out["rsi_7"] = float(ind.rsi(close, 7)[-1]) if len(close) > 7 else 50.0

            macd_l, sig_l, hist = ind.macd(close)
            out["macd_line"] = float(macd_l[-1]) if not np.isnan(macd_l[-1]) else 0.0
            out["macd_signal"] = float(sig_l[-1]) if not np.isnan(sig_l[-1]) else 0.0
            out["macd_histogram"] = float(hist[-1]) if not np.isnan(hist[-1]) else 0.0
            out["macd_crossover"] = 1.0 if out["macd_line"] > out["macd_signal"] else -1.0

            k, d = ind.stochastic(high, low, close)
            out["stoch_k"] = float(k[-1]) if not np.isnan(k[-1]) else 50.0
            out["stoch_d"] = float(d[-1]) if not np.isnan(d[-1]) else 50.0
            out["stoch_crossover"] = 1.0 if out["stoch_k"] > out["stoch_d"] else -1.0

            out["roc_10"] = float(ind.roc(close, 10)[-1]) if len(close) > 10 else 0.0
            out["roc_21"] = float(ind.roc(close, 21)[-1]) if len(close) > 21 else 0.0

            if len(close) >= 20:
                out["momentum_20"] = float(
                    (close[-1] - close[-20]) / close[-20] * 100.0
                ) if close[-20] != 0 else 0.0
            if len(close) >= 60:
                out["momentum_60"] = float(
                    (close[-1] - close[-60]) / close[-60] * 100.0
                ) if close[-60] != 0 else 0.0

            # Williams %R
            out["williams_r_14"] = float(ind.williams_r(high, low, close, 14)[-1]) if len(close) >= 14 else -50.0

            # CCI
            out["cci_20"] = float(ind.cci(high, low, close, 20)[-1]) if len(close) >= 20 else 0.0

        except Exception:
            pass
        return out

    def _compute_volatility(self, close: np.ndarray, high: np.ndarray,
                             low: np.ndarray) -> Dict[str, float]:
        out: Dict[str, float] = {}
        try:
            atr_14 = ind.atr(high, low, close, 14)
            last_close = close[-1]
            out["atr_14"] = float(atr_14[-1]) if not np.isnan(atr_14[-1]) else 0.0
            out["atr_14_pct"] = (out["atr_14"] / last_close * 100.0) if last_close != 0 else 0.0

            bb_upper, bb_mid, bb_lower = ind.bollinger_bands(close, 20, 2.0)
            bb_range = float(bb_upper[-1] - bb_lower[-1])
            out["bb_upper"] = float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else 0.0
            out["bb_lower"] = float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else 0.0
            out["bb_width"] = bb_range / float(bb_mid[-1]) if float(bb_mid[-1]) != 0 else 0.0
            out["bb_position"] = (
                (last_close - float(bb_lower[-1])) / bb_range if bb_range > 0 else 0.5
            )

            if len(close) >= 21:
                hv21 = ind.historical_volatility(close, 21)
                out["hv_21"] = float(hv21[-1]) if not np.isnan(hv21[-1]) else 0.0
            if len(close) >= 63:
                hv63 = ind.historical_volatility(close, 63)
                out["hv_63"] = float(hv63[-1]) if not np.isnan(hv63[-1]) else 0.0
                out["vol_ratio_21_63"] = (
                    out["hv_21"] / out["hv_63"] if out.get("hv_21") and out["hv_63"] != 0 else 1.0
                )

            # Hurst exponent (regime classifier)
            if len(close) >= 40:
                out["hurst"] = float(ind.hurst_exponent(close[-40:]))

            kc_upper, kc_mid, kc_lower = ind.keltner_channels(high, low, close)
            out["kc_squeeze"] = 1.0 if out["bb_width"] < float(
                (kc_upper[-1] - kc_lower[-1]) / kc_mid[-1]
                if kc_mid[-1] != 0 else 0.0
            ) else 0.0

        except Exception:
            pass
        return out

    def _compute_volume(self, close: np.ndarray, high: np.ndarray,
                         low: np.ndarray, volume: np.ndarray) -> Dict[str, float]:
        out: Dict[str, float] = {}
        try:
            vol_z = ind.volume_zscore(volume, 20)
            out["volume_zscore_20"] = float(vol_z[-1]) if not np.isnan(vol_z[-1]) else 0.0

            if len(volume) >= 2 and volume[-2] != 0:
                out["volume_change_pct"] = (volume[-1] - volume[-2]) / volume[-2] * 100.0
            else:
                out["volume_change_pct"] = 0.0

            obv_series = ind.obv(close, volume)
            obv_z = ind.zscore(obv_series, 20)
            out["obv_zscore_20"] = float(obv_z[-1]) if not np.isnan(obv_z[-1]) else 0.0

            cmf_series = ind.cmf(high, low, close, volume, 21)
            out["cmf_21"] = float(cmf_series[-1]) if not np.isnan(cmf_series[-1]) else 0.0

            # VWAP deviation
            vwap_val = ind.vwap(high, low, close, volume)[-1]
            out["vwap_dev_pct"] = (close[-1] - vwap_val) / vwap_val * 100.0 if vwap_val != 0 else 0.0

            # Volume MA ratio
            vol_sma = ind.sma(volume.astype(np.float64), 20)
            out["volume_sma_ratio"] = (
                volume[-1] / float(vol_sma[-1]) if not np.isnan(vol_sma[-1]) and vol_sma[-1] != 0 else 1.0
            )
        except Exception:
            pass
        return out

    def _compute_statistical(self, close: np.ndarray) -> Dict[str, float]:
        out: Dict[str, float] = {}
        try:
            log_ret = ind.log_returns(close)

            # Rolling Sharpe
            sh60 = ind.sharpe_rolling(log_ret, 60)
            out["sharpe_rolling_60"] = float(sh60[-1]) if not np.isnan(sh60[-1]) else 0.0

            # Rolling max drawdown
            dd60 = ind.max_drawdown_rolling(log_ret, 60)
            out["max_dd_rolling_60"] = float(dd60[-1]) if not np.isnan(dd60[-1]) else 0.0

            # Z-score of price
            pz20 = ind.zscore(close, 20)
            out["price_zscore_20"] = float(pz20[-1]) if not np.isnan(pz20[-1]) else 0.0

            # Autocorrelation at lag 1 (mean reversion indicator)
            if len(log_ret) >= 20:
                out["autocorr_lag1"] = float(np.corrcoef(log_ret[:-1], log_ret[1:])[0, 1])

            # Skewness and kurtosis of returns
            if len(log_ret) >= 20:
                mu = np.mean(log_ret)
                std = np.std(log_ret, ddof=1)
                if std > 0:
                    out["returns_skewness"] = float(
                        np.mean(((log_ret - mu) / std) ** 3)
                    )
                    out["returns_kurtosis"] = float(
                        np.mean(((log_ret - mu) / std) ** 4) - 3.0
                    )

        except Exception:
            pass
        return out
