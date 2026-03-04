"""Model loader and predictor for adaptive regime classification."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List


REGIMES = [
    "TRENDING_BULL",
    "TRENDING_BEAR",
    "RANGE_BOUND",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "CRASH_EVENT",
]


class _HeuristicModel:
    """Fallback model when no trained artifact is available."""

    def predict_proba(self, X: List[List[float]]) -> List[List[float]]:
        out = []
        for vector in X:
            trend = vector[6] if len(vector) > 6 else 0.0
            vol = vector[2] if len(vector) > 2 else 0.0
            vix = vector[11] if len(vector) > 11 else 0.5
            probs = {name: 0.0 for name in REGIMES}
            if vol > 0.8 or vix > 0.8:
                probs["CRASH_EVENT"] = 0.55 if trend < -0.2 else 0.25
                probs["HIGH_VOLATILITY"] = 0.55 if trend >= -0.2 else 0.35
                probs["TRENDING_BEAR"] = 0.20 if trend < -0.4 else 0.05
            elif abs(trend) > 0.45:
                if trend > 0:
                    probs["TRENDING_BULL"] = 0.65
                    probs["LOW_VOLATILITY"] = 0.10
                else:
                    probs["TRENDING_BEAR"] = 0.65
                    probs["LOW_VOLATILITY"] = 0.10
                probs["RANGE_BOUND"] = 0.15
            elif vol < 0.25:
                probs["LOW_VOLATILITY"] = 0.65
                probs["RANGE_BOUND"] = 0.25
            else:
                probs["RANGE_BOUND"] = 0.55
                probs["LOW_VOLATILITY"] = 0.20
                probs["HIGH_VOLATILITY"] = 0.10
            # Normalize
            total = sum(probs.values())
            if total <= 1e-9:
                probs["RANGE_BOUND"] = 1.0
                total = 1.0
            out.append([probs[name] / total for name in REGIMES])
        return out

    def predict(self, X: List[List[float]]) -> List[str]:
        probs = self.predict_proba(X)
        labels = []
        for row in probs:
            idx = max(range(len(row)), key=lambda i: row[i])
            labels.append(REGIMES[idx])
        return labels


class RegimeClassifier:
    """Loads trained model and predicts regime with probability."""

    def __init__(self, model_path: str = "quant_ecosystem/regime_ai/models/regime_model.pkl"):
        self.model_path = Path(model_path)
        self.model = self._load_model()

    def predict_regime(self, feature_vector: List[float]) -> str:
        return str(self.model.predict([feature_vector])[0]).upper()

    def predict_regime_probability(self, feature_vector: List[float]) -> Dict[str, float]:
        probs = self.model.predict_proba([feature_vector])[0]
        return {REGIMES[i]: float(probs[i]) for i in range(min(len(REGIMES), len(probs)))}

    def _load_model(self):
        if self.model_path.exists():
            try:
                with self.model_path.open("rb") as handle:
                    payload = pickle.load(handle)
                model = payload.get("model") if isinstance(payload, dict) else payload
                if hasattr(model, "predict") and hasattr(model, "predict_proba"):
                    return model
            except Exception:
                pass
        return _HeuristicModel()

