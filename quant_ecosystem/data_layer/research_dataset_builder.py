"""
research_dataset_builder.py
Builds labeled datasets for strategy research and model training.
Each row = (symbol, timestamp, feature_vector, forward_return_label).
Supports: classification labels (UP/DOWN), regression labels (return), ranking labels.
Outputs numpy arrays, pandas DataFrames, or JSON lines for downstream use.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from quant_ecosystem.feature_lab.feature_store import FeatureStore
from quant_ecosystem.feature_lab.feature_engineering_engine import FeatureEngineeringEngine

_DATASET_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "research_datasets"
_DATASET_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass
class ResearchSample:
    """One labeled training sample."""
    symbol: str
    timestamp: int
    features: Dict[str, float]
    forward_return_1: float   # 1-bar ahead log return
    forward_return_5: float   # 5-bar ahead log return
    forward_return_20: float  # 20-bar ahead log return
    regime: str = "UNKNOWN"
    label_1: int = 0          # +1 UP, -1 DOWN, 0 flat  (1-bar)
    label_5: int = 0          # 5-bar
    label_20: int = 0         # 20-bar

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "regime": self.regime,
            "forward_return_1": self.forward_return_1,
            "forward_return_5": self.forward_return_5,
            "forward_return_20": self.forward_return_20,
            "label_1": self.label_1,
            "label_5": self.label_5,
            "label_20": self.label_20,
            **{f"f_{k}": v for k, v in self.features.items()},
        }


class ResearchDatasetBuilder:
    """
    Builds feature-labeled datasets for supervised/IC research.

    Usage:
        builder = ResearchDatasetBuilder(feature_engine=feat_eng, feature_store=store)
        samples = builder.build(symbol="NSE:SBIN-EQ", timeframe="5m", lookback=500)
        X, y = builder.to_arrays(samples, label="label_5")
        builder.save(samples, name="sbin_5m_2026")
    """

    def __init__(
        self,
        feature_engine: Optional[FeatureEngineeringEngine] = None,
        feature_store: Optional[FeatureStore] = None,
        market_data_engine: Optional[Any] = None,
        label_threshold: float = 0.001,  # min abs return to assign UP/DOWN label, **kwargs
    ) -> None:
        self.feature_engine = feature_engine
        self.store = feature_store or FeatureStore()
        self.market_data = market_data_engine
        self._label_thresh = float(label_threshold)

    # ------------------------------------------------------------------
    # Build from market data
    # ------------------------------------------------------------------

    def build(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback: int = 500,
        regime: str = "UNKNOWN",
    ) -> List[ResearchSample]:
        """Build labeled samples for a symbol from OHLCV data."""
        if not self.market_data:
            return []
        try:
            snap = self.market_data.get_snapshot(symbol=symbol, lookback=lookback)
            if not snap:
                return []
        except Exception:
            return []

        close = np.array(snap.get("close", []), dtype=np.float64)
        high = np.array(snap.get("high", close), dtype=np.float64)
        low = np.array(snap.get("low", close), dtype=np.float64)
        volume = np.array(snap.get("volume", []), dtype=np.float64) if snap.get("volume") else None

        if len(close) < 50:
            return []

        # Compute log returns
        log_ret = np.log(close[1:] / np.where(close[:-1] == 0, 1e-10, close[:-1]))
        log_ret = np.insert(log_ret, 0, 0.0)

        # Forward returns at each time step
        samples = []
        feature_window = 60  # minimum history needed for features
        for i in range(feature_window, len(close) - 20):
            # Extract feature window ending at i
            c_win = close[max(0, i - 250) : i + 1]
            h_win = high[max(0, i - 250) : i + 1]
            lo_win = low[max(0, i - 250) : i + 1]
            v_win = volume[max(0, i - 250) : i + 1] if volume is not None else None

            features = self._compute_window_features(c_win, h_win, lo_win, v_win)
            if not features:
                continue

            # Forward returns
            fr1 = float(log_ret[i + 1]) if i + 1 < len(log_ret) else 0.0
            fr5 = float(np.sum(log_ret[i + 1 : i + 6])) if i + 5 < len(log_ret) else 0.0
            fr20 = float(np.sum(log_ret[i + 1 : i + 21])) if i + 19 < len(log_ret) else 0.0

            ts = int(time.time()) - (len(close) - i) * 300  # approx timestamp

            sample = ResearchSample(
                symbol=symbol,
                timestamp=ts,
                features=features,
                forward_return_1=round(fr1, 8),
                forward_return_5=round(fr5, 8),
                forward_return_20=round(fr20, 8),
                regime=regime,
                label_1=self._label(fr1),
                label_5=self._label(fr5),
                label_20=self._label(fr20),
            )
            samples.append(sample)

        return samples

    def build_multi_symbol(
        self,
        symbols: List[str],
        timeframe: str = "5m",
        lookback: int = 500,
        regime: str = "UNKNOWN",
    ) -> List[ResearchSample]:
        """Build combined dataset across multiple symbols."""
        all_samples = []
        for sym in symbols:
            samples = self.build(sym, timeframe, lookback, regime)
            all_samples.extend(samples)
        return all_samples

    # ------------------------------------------------------------------
    # Build from feature store (historical)
    # ------------------------------------------------------------------

    def build_from_store(
        self,
        symbol: str,
        timeframe: str,
        feature_names: List[str],
        last_n: int = 500,
    ) -> List[Dict[str, Any]]:
        """Build samples from persisted feature store data."""
        rows = []
        feature_data: Dict[str, List[Tuple[int, float]]] = {}
        for feat in feature_names:
            records = self.store.read_window(symbol, timeframe, feat, last_n)
            feature_data[feat] = records

        if not feature_data:
            return []

        # Align by timestamp
        ts_sets = [set(ts for ts, _ in records) for records in feature_data.values() if records]
        if not ts_sets:
            return []
        common_ts = sorted(ts_sets[0].intersection(*ts_sets[1:]))

        ts_map: Dict[str, Dict[int, float]] = {}
        for feat, records in feature_data.items():
            ts_map[feat] = {ts: v for ts, v in records}

        for ts in common_ts:
            row: Dict[str, Any] = {"symbol": symbol, "timeframe": timeframe, "timestamp": ts}
            for feat in feature_names:
                row[feat] = ts_map[feat].get(ts, 0.0)
            rows.append(row)

        return rows

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_arrays(
        self,
        samples: List[ResearchSample],
        label: str = "label_5",
        feature_names: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return (X, y) numpy arrays for ML training."""
        if not samples:
            return np.empty((0, 0)), np.empty(0)

        all_features = sorted(feature_names or list(samples[0].features.keys()))
        X = np.array([[s.features.get(f, 0.0) for f in all_features] for s in samples], dtype=np.float64)
        y = np.array([getattr(s, label, s.label_5) for s in samples], dtype=np.int32)

        # Replace NaN/inf
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        return X, y

    def to_dataframe(self, samples: List[ResearchSample]):
        """Return pandas DataFrame if pandas is available."""
        try:
            import pandas as pd
            return pd.DataFrame([s.to_dict() for s in samples])
        except ImportError:
            raise RuntimeError("pandas is required for to_dataframe()")

    def save(self, samples: List[ResearchSample], name: str) -> Path:
        """Save samples as JSON lines file."""
        path = _DATASET_ROOT / f"{name}.jsonl"
        with open(path, "w") as f:
            for s in samples:
                f.write(json.dumps(s.to_dict()) + "\n")
        return path

    def load(self, name: str) -> List[Dict[str, Any]]:
        """Load saved samples."""
        path = _DATASET_ROOT / f"{name}.jsonl"
        if not path.exists():
            return []
        rows = []
        with open(path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line.strip()))
                except Exception:
                    continue
        return rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _label(self, ret: float) -> int:
        if ret > self._label_thresh:
            return 1
        if ret < -self._label_thresh:
            return -1
        return 0

    def _compute_window_features(
        self,
        close: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        volume: Optional[np.ndarray],
    ) -> Optional[Dict[str, float]]:
        if self.feature_engine:
            # Use the full feature engine if available
            try:
                snap = {"close": close, "high": high, "low": low}
                if volume is not None:
                    snap["volume"] = volume
                # Build a mock snapshot and extract features
                from quant_ecosystem.feature_lab.feature_engineering_engine import FeatureEngineeringEngine
                fe = self.feature_engine
                return fe._compute_trend(close, high, low) | \
                       fe._compute_momentum(close, high, low) | \
                       fe._compute_volatility(close, high, low)
            except Exception:
                pass

        # Minimal inline computation (fallback)
        try:
            from quant_ecosystem.feature_lab import indicator_library as ind
            features: Dict[str, float] = {}
            if len(close) >= 14:
                rsi = ind.rsi(close, 14)
                features["rsi_14"] = float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0
            if len(close) >= 21:
                features["momentum_20"] = float(
                    (close[-1] - close[-20]) / close[-20] * 100
                ) if close[-20] != 0 else 0.0
            if len(close) >= 20:
                bb_u, bb_m, bb_l = ind.bollinger_bands(close, 20)
                if not np.isnan(bb_u[-1]):
                    features["bb_width"] = float((bb_u[-1] - bb_l[-1]) / bb_m[-1]) if bb_m[-1] != 0 else 0.04
            return features if features else None
        except Exception:
            return None
