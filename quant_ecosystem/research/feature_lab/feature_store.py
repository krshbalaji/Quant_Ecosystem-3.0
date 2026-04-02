"""
feature_store.py
Institutional-grade feature store with two-layer caching:
  Layer 1 — in-memory LRU cache per symbol/timeframe
  Layer 2 — disk-backed parquet store for persistence across sessions

Features are keyed by (symbol, timeframe, feature_name, timestamp_bucket).
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

_STORE_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "feature_store"
_STORE_ROOT.mkdir(parents=True, exist_ok=True)


class LRUCache:
    """Thread-safe LRU cache backed by OrderedDict."""

    def __init__(self, maxsize: int = 2048, **kwargs):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


class FeatureStore:
    """
    Two-layer feature store.
    
    Usage:
        store = FeatureStore()
        store.write("NSE:SBIN-EQ", "5m", "rsi_14", timestamp, 67.4)
        val = store.read("NSE:SBIN-EQ", "5m", "rsi_14", timestamp)
        df  = store.read_window("NSE:SBIN-EQ", "5m", "rsi_14", last_n=200)
    """

    _instance: Optional[FeatureStore] = None
    _lock = threading.Lock()

    def __new__(cls) -> FeatureStore:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, maxsize: int = 4096, ttl_seconds: int = 3600, **kwargs):
        if self._initialized:
            return
        self._cache = LRUCache(maxsize=maxsize)
        self._ttl = ttl_seconds
        self._expiry: Dict[str, float] = {}
        self._write_lock = threading.Lock()
        self._initialized = True

    # ------------------------------------------------------------------
    # Key construction
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(symbol: str, timeframe: str, feature: str,
                  timestamp: Optional[int] = None) -> str:
        ts = str(timestamp) if timestamp is not None else "latest"
        return f"{symbol}|{timeframe}|{feature}|{ts}"

    @staticmethod
    def _make_path(symbol: str, timeframe: str, feature: str) -> Path:
        safe_sym = symbol.replace(":", "_").replace("/", "_")
        return _STORE_ROOT / safe_sym / timeframe / f"{feature}.json"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write(self, symbol: str, timeframe: str, feature: str,
              timestamp: int, value: Any) -> None:
        key = self._make_key(symbol, timeframe, feature, timestamp)
        self._cache.set(key, value)
        self._expiry[key] = time.time() + self._ttl

        # Persist to disk (append-style JSON lines)
        path = self._make_path(symbol, timeframe, feature)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            with open(path, "a") as f:
                f.write(json.dumps({"ts": timestamp, "v": value}) + "\n")

    def write_vector(self, symbol: str, timeframe: str, feature: str,
                     timestamps: List[int], values: List[float]) -> None:
        """Batch write a time series — efficient for end-of-bar updates."""
        for ts, v in zip(timestamps, values):
            if not (np.isnan(v) if isinstance(v, float) else False):
                self.write(symbol, timeframe, feature, ts, v)

    def write_snapshot(self, symbol: str, timeframe: str,
                       timestamp: int, features: Dict[str, Any]) -> None:
        """Write multiple features for a single bar in one call."""
        for feat, val in features.items():
            self.write(symbol, timeframe, feat, timestamp, val)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read(self, symbol: str, timeframe: str, feature: str,
             timestamp: Optional[int] = None) -> Optional[Any]:
        key = self._make_key(symbol, timeframe, feature, timestamp)
        expiry = self._expiry.get(key, 0.0)
        if time.time() > expiry:
            self._cache.delete(key)
            return self._read_disk(symbol, timeframe, feature, timestamp)
        return self._cache.get(key)

    def _read_disk(self, symbol: str, timeframe: str, feature: str,
                   timestamp: Optional[int]) -> Optional[Any]:
        path = self._make_path(symbol, timeframe, feature)
        if not path.exists():
            return None
        try:
            with open(path) as f:
                lines = f.readlines()
            if timestamp is None:
                # Return most recent value
                for line in reversed(lines):
                    rec = json.loads(line.strip())
                    return rec["v"]
            for line in reversed(lines):
                rec = json.loads(line.strip())
                if rec["ts"] == timestamp:
                    return rec["v"]
        except Exception:
            pass
        return None

    def read_window(self, symbol: str, timeframe: str, feature: str,
                    last_n: int = 200) -> List[Tuple[int, float]]:
        """Return last N (timestamp, value) pairs from disk."""
        path = self._make_path(symbol, timeframe, feature)
        if not path.exists():
            return []
        try:
            with open(path) as f:
                lines = f.readlines()
            records = []
            for line in lines[-last_n:]:
                try:
                    rec = json.loads(line.strip())
                    records.append((rec["ts"], rec["v"]))
                except Exception:
                    continue
            return records
        except Exception:
            return []

    def read_array(self, symbol: str, timeframe: str, feature: str,
                   last_n: int = 200) -> np.ndarray:
        """Return only values as a numpy array."""
        records = self.read_window(symbol, timeframe, feature, last_n)
        return np.array([v for _, v in records], dtype=np.float64)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def list_features(self, symbol: str, timeframe: str) -> List[str]:
        safe_sym = symbol.replace(":", "_").replace("/", "_")
        base = _STORE_ROOT / safe_sym / timeframe
        if not base.exists():
            return []
        return [f.stem for f in base.glob("*.json")]

    def list_symbols(self) -> List[str]:
        return [d.name for d in _STORE_ROOT.iterdir() if d.is_dir()]

    def size(self) -> int:
        return len(self._cache)

    def clear_memory(self) -> None:
        self._cache.clear()
        self._expiry.clear()

    def purge_disk(self, symbol: str) -> None:
        """Remove all on-disk data for a symbol."""
        safe_sym = symbol.replace(":", "_").replace("/", "_")
        path = _STORE_ROOT / safe_sym
        import shutil
        if path.exists():
            shutil.rmtree(path)
