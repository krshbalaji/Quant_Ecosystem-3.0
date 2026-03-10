"""
quant_ecosystem/feature_lab/feature_lab.py
==========================================
Feature Lab — Quant Ecosystem 3.0

A modular, extensible feature engineering laboratory that transforms raw
market snapshots into structured feature vectors for use by strategies,
regime classifiers, and the MetaResearchAI layer.

Architecture
------------

    ┌──────────────────────────────────────────────────────────────────┐
    │                        FeatureLab                               │
    │   register / extract / select / score / cache / export          │
    └──────────────┬──────────────────────────────────────────────────┘
                   │  delegates to pluggable extractors
    ┌──────────────▼────────────────────────────────────────────────┐
    │  FeatureExtractor (protocol)                                  │
    │  ─────────────────────────────────────────────────────────── │
    │  PriceFeatureExtractor   — OHLCV, returns, volatility         │
    │  MomentumFeatureExtractor — RSI, momentum, rate-of-change     │
    │  VolatilityFeatureExtractor — ATR, Bollinger, HV              │
    │  VolumeFeatureExtractor  — OBV, VWAP deviation, vol z-score   │
    │  MicrostructureExtractor — bid-ask spread proxy, tick impact  │
    │  RegimeFeatureExtractor  — regime one-hot, transition proba   │
    └──────────────────────────────────────────────────────────────┘

Design principles
-----------------
- Zero third-party imports at module level (numpy optional, stdlib fallback).
- All extractors are registered by name; the lab composes them dynamically.
- Feature vectors are returned as ordered dicts (reproducible key order).
- A lightweight in-memory cache avoids re-computation on the same snapshot.
- Feature importance scoring supports wrapper-mode selection (correlation
  to target fitness, variance filtering).
- Fully injectable into StrategyDiscoveryEngine and MetaResearchAI.

Usage
-----
    lab = FeatureLab()
    lab.register(PriceFeatureExtractor())
    lab.register(MomentumFeatureExtractor())

    features = lab.extract(market_snapshot)
    vector   = lab.as_vector(features)          # list[float]
    selected = lab.select(features, k=20)       # top-k by importance
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_TAG = "[feature_lab]"


# ─────────────────────────────────────────────────────────────────────────────
# Protocols / Base classes
# ─────────────────────────────────────────────────────────────────────────────

class FeatureExtractor(ABC):
    """
    Base class for all feature extractors.

    Subclass and implement extract().  The method receives a raw
    market_snapshot dict and returns a flat dict of {feature_name: float}.
    """

    NAME: str = "base"

    @abstractmethod
    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract features from a market snapshot.

        Parameters
        ----------
        snapshot : dict
            Keys may include: open, high, low, close, volume, timestamp,
            prices (list), volumes (list), bid, ask, spread, regime, etc.

        Returns
        -------
        dict[str, float]  — flat feature dictionary
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.NAME!r})"


# ─────────────────────────────────────────────────────────────────────────────
# Built-in Extractors
# ─────────────────────────────────────────────────────────────────────────────

class PriceFeatureExtractor(FeatureExtractor):
    """OHLCV-based price features."""

    NAME = "price"

    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        o = _safe_float(snapshot.get("open",  snapshot.get("o", 0)))
        h = _safe_float(snapshot.get("high",  snapshot.get("h", 0)))
        l = _safe_float(snapshot.get("low",   snapshot.get("l", 0)))
        c = _safe_float(snapshot.get("close", snapshot.get("c", 0)))
        v = _safe_float(snapshot.get("volume",snapshot.get("v", 0)))

        prices: List[float] = [_safe_float(x) for x in snapshot.get("prices", [c])]
        n = len(prices)

        # Body / wick ratios
        candle_range = h - l if h > l else 1e-9
        body         = abs(c - o)
        upper_wick   = h - max(o, c)
        lower_wick   = min(o, c) - l

        # Simple returns
        ret_1  = _pct_change(prices, 1)
        ret_5  = _pct_change(prices, 5)
        ret_10 = _pct_change(prices, 10)
        ret_20 = _pct_change(prices, 20)

        # Historical volatility (20-period)
        hv20 = _hist_vol(prices, 20)

        # Distance from rolling high/low
        hi20 = max(prices[-20:]) if n >= 20 else max(prices)
        lo20 = min(prices[-20:]) if n >= 20 else min(prices)
        dist_hi = (hi20 - c) / hi20 if hi20 else 0.0
        dist_lo = (c - lo20) / lo20 if lo20 else 0.0

        return {
            "price_close":        c,
            "price_range":        candle_range,
            "price_body_ratio":   body / candle_range,
            "price_upper_wick":   upper_wick / candle_range,
            "price_lower_wick":   lower_wick / candle_range,
            "price_ret_1":        ret_1,
            "price_ret_5":        ret_5,
            "price_ret_10":       ret_10,
            "price_ret_20":       ret_20,
            "price_hv20":         hv20,
            "price_dist_hi20":    dist_hi,
            "price_dist_lo20":    dist_lo,
            "price_log_volume":   math.log1p(v),
        }


class MomentumFeatureExtractor(FeatureExtractor):
    """RSI, momentum, rate-of-change indicators."""

    NAME = "momentum"

    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        prices = [_safe_float(x) for x in snapshot.get("prices", [])]
        c      = _safe_float(snapshot.get("close", prices[-1] if prices else 0))
        if not prices:
            prices = [c]

        rsi_14 = _rsi(prices, 14)
        rsi_7  = _rsi(prices, 7)
        mom_10 = _momentum(prices, 10)
        mom_20 = _momentum(prices, 20)
        roc_10 = _roc(prices, 10)
        roc_20 = _roc(prices, 20)

        # MA crossover signal
        ma5   = _sma(prices, 5)
        ma20  = _sma(prices, 20)
        ma50  = _sma(prices, 50)
        cross_fast_slow = (ma5 - ma20) / ma20 if ma20 else 0.0
        price_vs_ma50   = (c - ma50) / ma50  if ma50 else 0.0

        return {
            "mom_rsi_14":          rsi_14,
            "mom_rsi_7":           rsi_7,
            "mom_rsi_14_norm":     (rsi_14 - 50.0) / 50.0,
            "mom_momentum_10":     mom_10,
            "mom_momentum_20":     mom_20,
            "mom_roc_10":          roc_10,
            "mom_roc_20":          roc_20,
            "mom_ma5":             ma5,
            "mom_ma20":            ma20,
            "mom_cross_fast_slow": cross_fast_slow,
            "mom_price_vs_ma50":   price_vs_ma50,
        }


class VolatilityFeatureExtractor(FeatureExtractor):
    """ATR, Bollinger Bands, and historical-volatility features."""

    NAME = "volatility"

    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        prices  = [_safe_float(x) for x in snapshot.get("prices", [])]
        highs   = [_safe_float(x) for x in snapshot.get("highs",  [])]
        lows    = [_safe_float(x) for x in snapshot.get("lows",   [])]
        c       = _safe_float(snapshot.get("close", prices[-1] if prices else 0))

        if not highs or len(highs) != len(prices):
            highs = prices
        if not lows  or len(lows) != len(prices):
            lows  = prices

        atr_14 = _atr(highs, lows, prices, 14)
        atr_pct = atr_14 / c if c else 0.0

        bb_upper, bb_mid, bb_lower = _bollinger(prices, 20, 2.0)
        bb_width = (bb_upper - bb_lower) / bb_mid if bb_mid else 0.0
        bb_pos   = (c - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) else 0.5

        hv5  = _hist_vol(prices, 5)
        hv10 = _hist_vol(prices, 10)
        hv20 = _hist_vol(prices, 20)
        vol_ratio = hv5 / hv20 if hv20 else 1.0

        return {
            "vol_atr_14":    atr_14,
            "vol_atr_pct":   atr_pct,
            "vol_bb_width":  bb_width,
            "vol_bb_pos":    bb_pos,
            "vol_hv5":       hv5,
            "vol_hv10":      hv10,
            "vol_hv20":      hv20,
            "vol_ratio_5_20": vol_ratio,
        }


class VolumeFeatureExtractor(FeatureExtractor):
    """OBV, VWAP deviation, volume z-score."""

    NAME = "volume"

    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        prices  = [_safe_float(x) for x in snapshot.get("prices",  [])]
        volumes = [_safe_float(x) for x in snapshot.get("volumes", [])]
        c       = _safe_float(snapshot.get("close",  prices[-1]  if prices  else 0))
        v       = _safe_float(snapshot.get("volume", volumes[-1] if volumes else 0))

        if not volumes or len(volumes) != len(prices):
            volumes = [v] * len(prices)
        if not prices:
            prices  = [c]

        # Volume z-score (20-period)
        vol_mean = _mean(volumes[-20:]) if len(volumes) >= 20 else _mean(volumes)
        vol_std  = _std(volumes[-20:])  if len(volumes) >= 20 else _std(volumes)
        vol_zscore = (v - vol_mean) / vol_std if vol_std else 0.0

        # OBV direction (simplified — recent trend over 10 bars)
        obv = _obv(prices, volumes)
        obv_10 = _sma(obv[-10:], 5) if len(obv) >= 10 else 0.0

        # VWAP deviation
        vwap = _vwap(prices, volumes)
        vwap_dev = (c - vwap) / vwap if vwap else 0.0

        # Volume-price confirmation
        ret = prices[-1] / prices[-2] - 1 if len(prices) >= 2 else 0.0
        vol_confirm = float(
            (ret > 0 and v > vol_mean) or (ret < 0 and v > vol_mean)
        )

        return {
            "vol_volume_zscore":    vol_zscore,
            "vol_obv_trend":        obv_10,
            "vol_vwap_dev":         vwap_dev,
            "vol_confirm":          vol_confirm,
            "vol_log_v":            math.log1p(v),
        }


class RegimeFeatureExtractor(FeatureExtractor):
    """Regime one-hot encoding and transition probability."""

    NAME = "regime"

    REGIMES = [
        "TRENDING", "RANGE_BOUND", "VOLATILE", "BREAKOUT",
        "BULL", "BEAR", "UNKNOWN",
    ]

    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        regime     = str(snapshot.get("regime",      "UNKNOWN")).upper()
        prev_regime= str(snapshot.get("prev_regime", "UNKNOWN")).upper()
        trans_prob = _safe_float(snapshot.get("transition_probability", 0.0))

        # One-hot
        features: Dict[str, float] = {}
        for r in self.REGIMES:
            features[f"regime_{r.lower()}"] = float(regime == r)

        # Transition features
        features["regime_transition_prob"]  = trans_prob
        features["regime_changed"]          = float(regime != prev_regime)
        features["regime_unknown"]          = float(regime == "UNKNOWN")

        return features


class MicrostructureExtractor(FeatureExtractor):
    """Bid-ask spread proxy and tick-level microstructure features."""

    NAME = "microstructure"

    def extract(self, snapshot: Dict[str, Any]) -> Dict[str, float]:
        bid    = _safe_float(snapshot.get("bid",    0))
        ask    = _safe_float(snapshot.get("ask",    0))
        c      = _safe_float(snapshot.get("close",  ask or bid or 1))
        spread = _safe_float(snapshot.get("spread", ask - bid if ask and bid else 0))
        ticks  = snapshot.get("tick_returns", [])

        mid    = (bid + ask) / 2 if (bid and ask) else c
        rel_spread = spread / mid if mid else 0.0

        tick_vol   = _std([_safe_float(t) for t in ticks]) if ticks else 0.0
        tick_dir   = _mean([1.0 if _safe_float(t) > 0 else -1.0 for t in ticks]) if ticks else 0.0

        return {
            "micro_relative_spread": rel_spread,
            "micro_mid":             mid,
            "micro_tick_vol":        tick_vol,
            "micro_tick_dir":        tick_dir,
            "micro_has_spread":      float(spread > 0),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Feature Importance Scorer
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureImportanceRecord:
    """Stores accumulated importance estimates for a single feature."""
    name:       str
    variance:   float = 0.0
    mean_abs:   float = 0.0
    corr_score: float = 0.0
    sample_count: int = 0

    @property
    def composite_score(self) -> float:
        return (self.variance * 0.4) + (self.mean_abs * 0.3) + (self.corr_score * 0.3)


class FeatureImportanceScorer:
    """
    Tracks per-feature variance and mean-absolute-value across multiple
    extraction calls, enabling lightweight variance-based feature selection.

    Optionally accepts a fitness_score alongside each feature dict to
    compute correlation-based importance estimates.
    """

    def __init__(self, decay: float = 0.05) -> None:
        """
        decay : float
            Exponential decay for the running statistics (0 = no decay).
        """
        self._decay = max(0.0, min(1.0, decay))
        self._records: Dict[str, FeatureImportanceRecord] = {}
        self._history: List[Tuple[Dict[str, float], float]] = []  # (features, fitness)
        self._max_history = 500

    def update(self, features: Dict[str, float], fitness: Optional[float] = None) -> None:
        """Update running statistics from a new feature observation."""
        for name, val in features.items():
            if name not in self._records:
                self._records[name] = FeatureImportanceRecord(name=name)
            rec = self._records[name]
            d   = self._decay

            # Running mean-abs
            rec.mean_abs   = rec.mean_abs   * (1 - d) + abs(val) * d
            # Running variance (approximate)
            rec.variance   = rec.variance   * (1 - d) + (val ** 2) * d
            rec.sample_count += 1

        if fitness is not None:
            self._history.append((dict(features), fitness))
            if len(self._history) > self._max_history:
                self._history.pop(0)
            self._recompute_correlations()

    def _recompute_correlations(self) -> None:
        if len(self._history) < 10:
            return
        fitnesses = [h[1] for h in self._history]
        for name in self._records:
            vals = [h[0].get(name, 0.0) for h in self._history]
            self._records[name].corr_score = abs(_pearson(vals, fitnesses))

    def top_features(self, k: int = 20) -> List[str]:
        """Return names of top-k features by composite importance score."""
        ranked = sorted(
            self._records.values(),
            key=lambda r: r.composite_score,
            reverse=True,
        )
        return [r.name for r in ranked[:k]]

    def scores(self) -> Dict[str, float]:
        return {name: rec.composite_score for name, rec in self._records.items()}


# ─────────────────────────────────────────────────────────────────────────────
# FeatureLab
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureLabConfig:
    enable_cache:   bool  = True
    cache_max_size: int   = 1000
    cache_ttl_sec:  float = 5.0
    importance_decay: float = 0.05
    default_extractors: bool = True   # auto-register built-in extractors


class FeatureLab:
    """
    Central feature engineering laboratory.

    Register extractors, extract feature dicts, score importance,
    select top-k features, and export ordered vectors.

    Fully injectable — pass an instance to StrategyDiscoveryEngine,
    MetaResearchAI, or any other engine that needs feature vectors.
    """

    def __init__(
        self,
        cfg: Optional[FeatureLabConfig] = None,
        **kwargs,
    ) -> None:
        self._cfg      = cfg or FeatureLabConfig()
        self._extractors: Dict[str, FeatureExtractor] = {}
        self._scorer   = FeatureImportanceScorer(decay=self._cfg.importance_decay)

        # Simple TTL cache: {hash: (timestamp, features)}
        self._cache: Dict[str, Tuple[float, Dict[str, float]]] = {}

        if self._cfg.default_extractors:
            for ext in _DEFAULT_EXTRACTORS:
                self.register(ext)

        logger.info(
            "%s FeatureLab initialized | extractors=%s | cache=%s",
            _TAG, list(self._extractors.keys()), self._cfg.enable_cache,
        )

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, extractor: FeatureExtractor) -> None:
        """Add or replace an extractor."""
        if not isinstance(extractor, FeatureExtractor):
            raise TypeError(f"Expected FeatureExtractor, got {type(extractor)}")
        self._extractors[extractor.NAME] = extractor
        logger.debug("%s Registered extractor: %s", _TAG, extractor.NAME)

    def unregister(self, name: str) -> bool:
        """Remove an extractor by name."""
        if name in self._extractors:
            del self._extractors[name]
            return True
        return False

    def extractor_names(self) -> List[str]:
        return list(self._extractors.keys())

    # ── Extraction ────────────────────────────────────────────────────────────

    def extract(
        self,
        snapshot: Dict[str, Any],
        extractor_names: Optional[List[str]] = None,
        fitness: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Run all (or a named subset of) extractors on *snapshot*.

        Parameters
        ----------
        snapshot        : market snapshot dict
        extractor_names : limit to these extractors (None = all)
        fitness         : optional fitness score for importance tracking

        Returns
        -------
        OrderedDict[str, float]  — merged, sorted feature dict
        """
        # Cache lookup
        if self._cfg.enable_cache:
            cache_key = self._snapshot_hash(snapshot)
            hit = self._cache.get(cache_key)
            if hit:
                ts, cached = hit
                if (time.monotonic() - ts) < self._cfg.cache_ttl_sec:
                    return dict(cached)
            self._evict_cache()

        names = extractor_names or list(self._extractors.keys())
        merged: Dict[str, float] = {}

        for name in names:
            ext = self._extractors.get(name)
            if ext is None:
                logger.debug("%s Extractor not found: %s", _TAG, name)
                continue
            try:
                feats = ext.extract(snapshot)
                merged.update(feats)
            except Exception as exc:
                logger.warning("%s Extractor %s failed: %s", _TAG, name, exc)

        ordered = OrderedDict(sorted(merged.items()))

        # Update importance scorer
        self._scorer.update(ordered, fitness=fitness)

        # Cache store
        if self._cfg.enable_cache:
            self._cache[cache_key] = (time.monotonic(), dict(ordered))

        return dict(ordered)

    # ── Vector export ─────────────────────────────────────────────────────────

    def as_vector(self, features: Dict[str, float]) -> List[float]:
        """Return feature values as a sorted list (reproducible order)."""
        return [features[k] for k in sorted(features)]

    def as_named_vector(self, features: Dict[str, float]) -> List[Tuple[str, float]]:
        """Return (name, value) pairs in sorted order."""
        return [(k, features[k]) for k in sorted(features)]

    # ── Feature selection ─────────────────────────────────────────────────────

    def select(
        self,
        features: Dict[str, float],
        k: int = 20,
    ) -> Dict[str, float]:
        """
        Return the top-k features by composite importance score.
        Falls back to full feature dict if scorer has insufficient history.
        """
        top_names = self._scorer.top_features(k=k)
        if not top_names:
            # Not enough history yet — return all features
            return dict(features)
        return {name: features[name] for name in top_names if name in features}

    # ── Importance ────────────────────────────────────────────────────────────

    def importance_scores(self) -> Dict[str, float]:
        """Return composite importance score per feature name."""
        return self._scorer.scores()

    def top_feature_names(self, k: int = 20) -> List[str]:
        return self._scorer.top_features(k=k)

    # ── Normalization ─────────────────────────────────────────────────────────

    def normalize(
        self,
        features: Dict[str, float],
        method: str = "clip",
    ) -> Dict[str, float]:
        """
        Normalize feature values.

        method : "clip"   — clip to [-3, 3] and divide by 3 → [-1, 1]
                 "tanh"   — tanh squashing
                 "none"   — pass through
        """
        if method == "none":
            return dict(features)

        out = {}
        for k, v in features.items():
            if math.isnan(v) or math.isinf(v):
                out[k] = 0.0
                continue
            if method == "clip":
                out[k] = max(-1.0, min(1.0, v / 3.0))
            elif method == "tanh":
                out[k] = math.tanh(v)
            else:
                out[k] = v
        return out

    # ── Cache internals ───────────────────────────────────────────────────────

    def _snapshot_hash(self, snapshot: Dict[str, Any]) -> str:
        # Hash only stable scalar fields for cache key
        key_fields = {
            k: snapshot[k]
            for k in ("close", "open", "high", "low", "volume", "timestamp")
            if k in snapshot
        }
        raw = str(sorted(key_fields.items())).encode()
        return hashlib.md5(raw).hexdigest()

    def _evict_cache(self) -> None:
        if len(self._cache) <= self._cfg.cache_max_size:
            return
        now = time.monotonic()
        expired = [
            k for k, (ts, _) in self._cache.items()
            if (now - ts) > self._cfg.cache_ttl_sec
        ]
        for k in expired:
            del self._cache[k]
        # Hard trim if still oversized
        while len(self._cache) > self._cfg.cache_max_size:
            self._cache.pop(next(iter(self._cache)))

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "extractors":       list(self._extractors.keys()),
            "extractor_count":  len(self._extractors),
            "cache_size":       len(self._cache),
            "scored_features":  len(self._scorer.scores()),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Default extractor list (instantiated once)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_EXTRACTORS: List[FeatureExtractor] = [
    PriceFeatureExtractor(),
    MomentumFeatureExtractor(),
    VolatilityFeatureExtractor(),
    VolumeFeatureExtractor(),
    RegimeFeatureExtractor(),
    MicrostructureExtractor(),
]


# ─────────────────────────────────────────────────────────────────────────────
# Pure math helpers (stdlib only, no numpy)
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m  = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _pct_change(prices: List[float], n: int) -> float:
    if len(prices) <= n or prices[-n - 1] == 0:
        return 0.0
    return prices[-1] / prices[-n - 1] - 1.0


def _sma(prices: List[float], n: int) -> float:
    if not prices:
        return 0.0
    window = prices[-n:] if len(prices) >= n else prices
    return _mean(window)


def _hist_vol(prices: List[float], n: int) -> float:
    if len(prices) < n + 1:
        return 0.0
    rets = [
        math.log(prices[i] / prices[i - 1])
        for i in range(max(1, len(prices) - n), len(prices))
        if prices[i - 1] > 0
    ]
    return _std(rets) * math.sqrt(252) if rets else 0.0


def _rsi(prices: List[float], n: int) -> float:
    if len(prices) < n + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(len(prices) - n, len(prices))]
    gains  = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_gain = _mean(gains) if gains else 0.0
    avg_loss = _mean(losses) if losses else 1e-9
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _momentum(prices: List[float], n: int) -> float:
    if len(prices) <= n:
        return 0.0
    return prices[-1] - prices[-n - 1]


def _roc(prices: List[float], n: int) -> float:
    if len(prices) <= n or prices[-n - 1] == 0:
        return 0.0
    return (prices[-1] - prices[-n - 1]) / prices[-n - 1] * 100.0


def _atr(highs: List[float], lows: List[float], closes: List[float], n: int) -> float:
    if len(closes) < 2 or len(highs) < 2 or len(lows) < 2:
        return 0.0
    trs = []
    for i in range(max(1, len(closes) - n), len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return _mean(trs)


def _bollinger(prices: List[float], n: int, k: float) -> Tuple[float, float, float]:
    mid   = _sma(prices, n)
    sigma = _std(prices[-n:]) if len(prices) >= n else _std(prices)
    return mid + k * sigma, mid, mid - k * sigma


def _obv(prices: List[float], volumes: List[float]) -> List[float]:
    obv = [0.0]
    for i in range(1, min(len(prices), len(volumes))):
        if prices[i] > prices[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif prices[i] < prices[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def _vwap(prices: List[float], volumes: List[float]) -> float:
    n = min(len(prices), len(volumes))
    if n == 0:
        return 0.0
    total_vol = sum(volumes[:n])
    if total_vol == 0:
        return 0.0
    return sum(prices[i] * volumes[i] for i in range(n)) / total_vol


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx, my = _mean(xs[:n]), _mean(ys[:n])
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx  = math.sqrt(sum((x - mx) ** 2 for x in xs[:n]))
    dy  = math.sqrt(sum((y - my) ** 2 for y in ys[:n]))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)
