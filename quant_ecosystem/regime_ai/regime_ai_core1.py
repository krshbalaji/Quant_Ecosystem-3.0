"""Adaptive Market Regime AI core engine with rule fallback."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from quant_ecosystem.regime_ai.feature_engineer import FeatureEngineer
from quant_ecosystem.regime_ai.regime_classifier import RegimeClassifier


class AdaptiveRegimeEngine:
    """AI-first regime detection with deterministic rule fallback."""

    def __init__(
        self,
        model_path: str = "quant_ecosystem/regime_ai/models/regime_model.pkl",
        min_confidence: float = 0.45,
        feature_engineer: FeatureEngineer | None = None,
        classifier: RegimeClassifier | None = None,
        rule_detector=None,
    ):
        self.model_path = model_path
        self.min_confidence = float(min_confidence)
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.classifier = classifier or RegimeClassifier(model_path=model_path)
        self.rule_detector = rule_detector
        self._state: Dict = {
            "regime": "RANGE_BOUND",
            "probability": 0.0,
            "volatility_score": 0.0,
            "trend_score": 0.0,
            "source": "INIT",
            "timestamp": None,
        }

    def detect_regime(self, timeframe_data: Dict[str, Dict], extra_signals: Optional[Dict] = None) -> Dict:
        """Detect regime using ML model; fallback to rule engine if confidence is low."""
        extra = extra_signals or {}
        merged = self._merge_timeframes(timeframe_data)
        if not merged.get("close"):
            return self.get_regime_state()

        raw = self.feature_engineer.build_feature_vector(merged, extra_signals=extra)
        norm = self.feature_engineer.normalize_features(raw)
        vector = self.feature_engineer.as_ordered_vector(norm)

        regime = self.classifier.predict_regime(vector)
        probs = self.classifier.predict_regime_probability(vector)
        probability = float(probs.get(regime, 0.0))
        source = "AI"

        if probability < self.min_confidence and self.rule_detector is not None:
            try:
                fallback = self.rule_detector.detect_regime(timeframe_data=timeframe_data, extra_signals=extra)
                regime = str(fallback.get("regime", regime)).upper()
                probability = max(probability, float(fallback.get("confidence", 0.0)))
                source = "RULE_FALLBACK"
            except Exception:
                pass

        self._state = {
            "regime": regime,
            "probability": round(probability, 4),
            "volatility_score": round(float(norm.get("rolling_vol", 0.0)), 4),
            "trend_score": round(float(norm.get("trend_slope", 0.0)), 4),
            "source": source,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return dict(self._state)

    def get_regime_state(self) -> Dict:
        return dict(self._state)

    def broadcast_regime(
        self,
        payload: Optional[Dict] = None,
        strategy_bank_layer=None,
        strategy_selector=None,
        meta_strategy_brain=None,
        capital_allocator_engine=None,
        autonomous_controller=None,
    ) -> Dict:
        """Broadcast regime to dependent engines with loose coupling."""
        data = payload or self.get_regime_state()
        regime = str(data.get("regime", "RANGE_BOUND")).upper()

        if strategy_bank_layer and hasattr(strategy_bank_layer, "is_enabled") and strategy_bank_layer.is_enabled():
            try:
                rows = strategy_bank_layer.registry_rows()
                for row in rows:
                    row["last_regime"] = regime
                    strategy_bank_layer.bank_engine.registry.upsert(row)
                strategy_bank_layer.bank_engine.registry.save()
            except Exception:
                pass

        if strategy_selector is not None:
            try:
                setattr(strategy_selector, "regime_source", lambda: regime)
            except Exception:
                pass

        if meta_strategy_brain is not None:
            try:
                setattr(meta_strategy_brain, "last_regime", regime)
            except Exception:
                pass

        if capital_allocator_engine is not None:
            try:
                setattr(capital_allocator_engine, "last_regime", regime)
            except Exception:
                pass

        if autonomous_controller is not None:
            try:
                setattr(autonomous_controller, "last_regime", regime)
            except Exception:
                pass

        return data

    def _merge_timeframes(self, timeframe_data: Dict[str, Dict]) -> Dict:
        order = ["5m", "15m", "1h", "1d"]
        merged = {"close": [], "high": [], "low": [], "volume": [], "spread": []}
        for tf in order:
            bucket = timeframe_data.get(tf, {})
            for key in merged.keys():
                values = list(bucket.get(key, []))
                if not values:
                    continue
                # Keep latest window weighted toward shorter TF by appending.
                merged[key].extend(values[-40:])
        # Trim to stable size.
        for key in merged.keys():
            merged[key] = merged[key][-200:]
        return merged



# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class RegimeAICore:
    """Minimal SystemFactory entry-point for regime detection.

    Delegates to :class:`AdaptiveRegimeEngine` when available; falls
    back to returning ``"RANGE_BOUND"`` so the system always has a regime.
    """

    _FALLBACK_REGIME = "RANGE_BOUND"

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = AdaptiveRegimeEngine()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("RegimeAICore: delegate unavailable (%s) — stub mode", exc)
        self._log.info("RegimeAICore initialized")

    def detect_regime(self, market_data: dict | None = None) -> str:
        """Detect the current market regime from *market_data*.

        Returns a regime string (e.g. ``"TRENDING_UP"``, ``"RANGE_BOUND"``).
        Never raises; returns the fallback regime on any failure.
        """
        if self._delegate is not None:
            try:
                result = self._delegate.detect(market_data=market_data or {})
                return result.get("regime", self._FALLBACK_REGIME) if isinstance(result, dict) else str(result)
            except Exception as exc:  # noqa: BLE001
                self._log.warning("RegimeAICore.detect_regime: delegate error (%s)", exc)
        return self._FALLBACK_REGIME
