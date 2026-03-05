"""
regime_detection_engine.py
Multi-timeframe, multi-indicator regime classification.
Produces a canonical RegimeState that drives strategy selection, capital allocation,
and signal filtering across the entire ecosystem.

Regimes:
  TRENDING_BULL       → strong uptrend, high momentum
  TRENDING_BEAR       → strong downtrend, high negative momentum
  RANGE_BOUND         → sideways, mean-reverting, low trend
  HIGH_VOLATILITY     → elevated vol, increased risk, breakout potential
  LOW_VOLATILITY      → compressed vol, momentum strategies less effective
  CRASH_EVENT         → extreme tail event detected
  TRANSITION          → mixed signals, regime changing

Detection layers:
  1. Trend layer       (MA alignment, ADX proxy, momentum)
  2. Volatility layer  (HV ratio, ATR percentile, BB width)
  3. Statistical layer (Hurst exponent, autocorrelation)
  4. Volume layer      (volume zscore, OBV trend)
  5. Ensemble vote     (weighted majority across layers)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from quant_ecosystem.feature_lab import indicator_library as ind


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

REGIME_LIST = [
    "TRENDING_BULL", "TRENDING_BEAR", "RANGE_BOUND",
    "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRASH_EVENT", "TRANSITION",
]


@dataclass
class RegimeState:
    """Full regime classification output."""
    regime: str                          # canonical regime label
    confidence: float                    # [0, 1]
    sub_regime: str = ""                 # optional finer label
    trend_score: float = 0.0             # -1 (bear) to +1 (bull)
    volatility_level: str = "NORMAL"     # LOW | NORMAL | HIGH | EXTREME
    hurst: float = 0.5
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "confidence": round(self.confidence, 4),
            "sub_regime": self.sub_regime,
            "trend_score": round(self.trend_score, 4),
            "volatility_level": self.volatility_level,
            "hurst": round(self.hurst, 4),
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }

    def regime_advanced(self) -> str:
        """Canonical name used by the orchestrator's regime broadcast."""
        return self.regime


# ---------------------------------------------------------------------------
# Layer evaluators
# ---------------------------------------------------------------------------

class TrendLayer:
    """Evaluates trend direction and strength."""

    def evaluate(self, close: np.ndarray) -> Dict[str, Any]:
        if len(close) < 50:
            return {"score": 0.0, "label": "NEUTRAL"}

        e9 = ind.ema(close, 9)
        e21 = ind.ema(close, 21)
        e50 = ind.ema(close, 50)

        if np.isnan(e9[-1]) or np.isnan(e21[-1]) or np.isnan(e50[-1]):
            return {"score": 0.0, "label": "NEUTRAL"}

        # Alignment score: -3 to +3
        alignment = (
            (1 if e9[-1] > e21[-1] else -1) +
            (1 if e21[-1] > e50[-1] else -1) +
            (1 if close[-1] > e50[-1] else -1)
        )
        norm_alignment = alignment / 3.0

        # Momentum at multiple horizons
        mom20 = (close[-1] - close[-20]) / abs(close[-20]) if close[-20] != 0 else 0.0
        mom60 = (close[-1] - close[-60]) / abs(close[-60]) if len(close) >= 60 and close[-60] != 0 else 0.0

        # Slope of long MA
        slope = (e50[-1] - e50[-5]) / abs(e50[-5]) if abs(e50[-5]) > 0 and len(e50) >= 5 else 0.0

        score = (norm_alignment * 0.50 + np.sign(mom20) * min(abs(mom20) * 20, 1.0) * 0.30 +
                 np.sign(slope) * min(abs(slope) * 50, 1.0) * 0.20)

        if score > 0.5:
            label = "BULL"
        elif score < -0.5:
            label = "BEAR"
        elif abs(score) < 0.2:
            label = "RANGE"
        else:
            label = "WEAK_TREND"

        return {
            "score": round(float(score), 4),
            "label": label,
            "alignment": alignment,
            "mom20": round(float(mom20 * 100), 4),
            "mom60": round(float(mom60 * 100), 4),
        }


class VolatilityLayer:
    """Evaluates current volatility regime."""

    def evaluate(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, Any]:
        if len(close) < 30:
            return {"level": "NORMAL", "score": 0.5, "percentile": 50.0}

        # Historical volatility
        hv21 = ind.historical_volatility(close, 21)
        hv63 = ind.historical_volatility(close, min(63, len(close) - 1))

        hv_current = float(hv21[-1]) if not np.isnan(hv21[-1]) else 0.20
        hv_long = float(hv63[-1]) if not np.isnan(hv63[-1]) else 0.20

        # HV ratio
        hv_ratio = hv_current / hv_long if hv_long > 0 else 1.0

        # BB width as vol proxy
        bb_u, bb_m, bb_l = ind.bollinger_bands(close, 20)
        bb_width = float((bb_u[-1] - bb_l[-1]) / bb_m[-1]) if not np.isnan(bb_m[-1]) and bb_m[-1] != 0 else 0.04

        # ATR pct
        atr_v = ind.atr(high, low, close, 14)
        atr_pct = float(atr_v[-1] / close[-1] * 100) if not np.isnan(atr_v[-1]) and close[-1] != 0 else 1.5

        # Extreme move detection
        daily_rets = np.abs(np.diff(close) / np.where(close[:-1] == 0, 1e-10, close[:-1]))
        recent_max = float(np.max(daily_rets[-5:])) if len(daily_rets) >= 5 else 0.0
        is_crash = recent_max > 0.05 or hv_ratio > 2.5

        # Composite vol score [0, 1]: 0 = low vol, 1 = extreme vol
        score = min(1.0, (hv_ratio - 0.5) * 0.5 + atr_pct * 0.15 + bb_width * 5.0)

        if is_crash:
            level = "EXTREME"
        elif score > 0.75:
            level = "HIGH"
        elif score < 0.25:
            level = "LOW"
        else:
            level = "NORMAL"

        return {
            "level": level,
            "score": round(float(score), 4),
            "hv_ratio": round(float(hv_ratio), 4),
            "atr_pct": round(float(atr_pct), 4),
            "is_crash": is_crash,
        }


class StatisticalLayer:
    """Evaluates mean-reversion vs trending via Hurst and autocorrelation."""

    def evaluate(self, close: np.ndarray) -> Dict[str, Any]:
        if len(close) < 40:
            return {"hurst": 0.5, "autocorr": 0.0, "regime_hint": "UNKNOWN"}

        hurst = ind.hurst_exponent(close[-60:] if len(close) >= 60 else close)
        log_ret = ind.log_returns(close)
        autocorr = float(np.corrcoef(log_ret[:-1], log_ret[1:])[0, 1]) if len(log_ret) > 5 else 0.0

        if hurst > 0.60:
            hint = "TRENDING"
        elif hurst < 0.40:
            hint = "MEAN_REVERTING"
        else:
            hint = "RANDOM_WALK"

        return {
            "hurst": round(float(hurst), 4),
            "autocorr": round(float(autocorr), 4),
            "regime_hint": hint,
        }


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class RegimeDetectionEngine:
    """
    Ensemble regime detector combining trend, volatility, and statistical layers.

    Usage:
        engine = RegimeDetectionEngine()
        state = engine.detect(close=arr, high=arr, low=arr, volume=arr)
        print(state.regime, state.confidence)

    Integration with orchestrator:
        The orchestrator calls _detect_and_broadcast_regime, which uses market_regime_detector.
        Replace or augment that with RegimeDetectionEngine by registering it on the router:
          router.market_regime_detector = RegimeDetectionEngine()
    """

    def __init__(
        self,
        smoothing_alpha: float = 0.3,
        min_confidence: float = 0.50,
    ) -> None:
        self._trend_layer = TrendLayer()
        self._vol_layer = VolatilityLayer()
        self._stat_layer = StatisticalLayer()
        self._smooth_alpha = float(smoothing_alpha)
        self._min_confidence = float(min_confidence)
        self._last_state: Optional[RegimeState] = None
        self._history: List[RegimeState] = []

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(
        self,
        close: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        volume: Optional[np.ndarray] = None,
    ) -> RegimeState:
        """Detect regime from OHLCV arrays."""
        high_ = high if high is not None else close
        low_ = low if low is not None else close

        trend_ev = self._trend_layer.evaluate(close)
        vol_ev = self._vol_layer.evaluate(close, high_, low_)
        stat_ev = self._stat_layer.evaluate(close)

        regime, confidence = self._ensemble_vote(trend_ev, vol_ev, stat_ev)

        # Temporal smoothing: don't flip regime on a single noisy bar
        if self._last_state and confidence < 0.70:
            prev_regime = self._last_state.regime
            if prev_regime != regime:
                # Blend toward new regime — require two consecutive detections
                regime = "TRANSITION"
                confidence = (confidence + self._last_state.confidence) / 2

        trend_score = float(trend_ev["score"])
        hurst = float(stat_ev["hurst"])
        vol_level = str(vol_ev["level"])

        state = RegimeState(
            regime=regime,
            confidence=round(confidence, 4),
            trend_score=trend_score,
            volatility_level=vol_level,
            hurst=hurst,
            evidence={
                "trend": trend_ev,
                "volatility": vol_ev,
                "statistical": stat_ev,
            },
        )

        self._last_state = state
        self._history.append(state)
        if len(self._history) > 500:
            self._history = self._history[-200:]

        return state

    def detect_from_snapshots(
        self, snapshots: List[Dict[str, Any]], timeframe: str = "5m"
    ) -> RegimeState:
        """Accept the snapshot format used by the orchestrator."""
        for snap in snapshots:
            if snap.get("timeframe", "5m") == timeframe:
                close = np.array(snap.get("close", []), dtype=np.float64)
                high = np.array(snap.get("high", close), dtype=np.float64)
                low = np.array(snap.get("low", close), dtype=np.float64)
                if len(close) >= 30:
                    return self.detect(close, high, low)
        return self._last_state or RegimeState(regime="LOW_VOLATILITY", confidence=0.5)

    # Compatibility with orchestrator's market_regime_detector interface
    def detect_regime(
        self,
        timeframe_data: Dict[str, Any],
        extra_signals: Optional[Dict[str, Any]] = None,
    ) -> RegimeState:
        """Orchestrator-compatible interface."""
        for tf in ["5m", "15m", "1h", "1d"]:
            data = timeframe_data.get(tf, {})
            close = np.array(data.get("close", []), dtype=np.float64)
            if len(close) >= 30:
                high = np.array(data.get("high", close), dtype=np.float64)
                low = np.array(data.get("low", close), dtype=np.float64)
                state = self.detect(close, high, low)
                return state
        return RegimeState(regime="LOW_VOLATILITY", confidence=0.5)

    def broadcast_regime(
        self,
        state: RegimeState,
        strategy_bank_layer: Optional[Any] = None,
        strategy_selector: Optional[Any] = None,
        meta_strategy_brain: Optional[Any] = None,
        capital_allocator_engine: Optional[Any] = None,
        autonomous_controller: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Propagate regime to all downstream consumers."""
        regime = state.regime
        for target in [strategy_bank_layer, strategy_selector, meta_strategy_brain,
                       capital_allocator_engine, autonomous_controller]:
            if target is None:
                continue
            for method in ["on_regime_change", "update_regime", "set_regime"]:
                if hasattr(target, method):
                    try:
                        getattr(target, method)(regime)
                    except Exception:
                        pass
                    break

    # ------------------------------------------------------------------
    # Ensemble vote
    # ------------------------------------------------------------------

    def _ensemble_vote(
        self,
        trend_ev: Dict[str, Any],
        vol_ev: Dict[str, Any],
        stat_ev: Dict[str, Any],
    ) -> Tuple[str, float]:
        """Combine layer evidence into a single regime label + confidence."""
        trend_label = str(trend_ev.get("label", "NEUTRAL"))
        vol_level = str(vol_ev.get("level", "NORMAL"))
        stat_hint = str(stat_ev.get("regime_hint", "UNKNOWN"))
        vol_score = float(vol_ev.get("score", 0.5))
        trend_score = float(trend_ev.get("score", 0.0))
        hurst = float(stat_ev.get("hurst", 0.5))
        is_crash = bool(vol_ev.get("is_crash", False))

        # Crash override
        if is_crash:
            return "CRASH_EVENT", 0.90

        # High volatility override
        if vol_level == "HIGH" or (vol_level == "EXTREME" and not is_crash):
            return "HIGH_VOLATILITY", min(0.95, 0.60 + vol_score * 0.4)

        # Trending regimes
        if trend_label == "BULL" and hurst > 0.50:
            conf = min(0.95, 0.55 + abs(trend_score) * 0.4)
            return "TRENDING_BULL", conf
        if trend_label == "BEAR" and hurst > 0.50:
            conf = min(0.95, 0.55 + abs(trend_score) * 0.4)
            return "TRENDING_BEAR", conf

        # Mean-reverting / range-bound
        if stat_hint == "MEAN_REVERTING" or trend_label == "RANGE":
            conf = min(0.90, 0.50 + (0.5 - hurst) * 1.2)
            return "RANGE_BOUND", max(0.50, conf)

        # Low vol
        if vol_level == "LOW":
            return "LOW_VOLATILITY", 0.65

        # Weak trend — treat as range
        if trend_label in ("WEAK_TREND", "NEUTRAL"):
            return "RANGE_BOUND", 0.55

        return "TRANSITION", 0.50

    # ------------------------------------------------------------------
    # History and diagnostics
    # ------------------------------------------------------------------

    def recent_regimes(self, n: int = 10) -> List[str]:
        return [s.regime for s in self._history[-n:]]

    def regime_stability(self, n: int = 20) -> float:
        """Fraction of last n detections that agree with current regime."""
        if not self._last_state or len(self._history) < 2:
            return 1.0
        recent = self.recent_regimes(n)
        current = self._last_state.regime
        return sum(1 for r in recent if r == current) / len(recent)

    def last_state(self) -> Optional[RegimeState]:
        return self._last_state
