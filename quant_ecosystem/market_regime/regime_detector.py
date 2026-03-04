"""Independent market regime detector service with multi-timeframe support."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional

from quant_ecosystem.market_regime.liquidity_analyzer import LiquidityAnalyzer
from quant_ecosystem.market_regime.regime_classifier import RegimeClassifier
from quant_ecosystem.market_regime.trend_analyzer import TrendAnalyzer
from quant_ecosystem.market_regime.volatility_analyzer import VolatilityAnalyzer


class MarketRegimeDetector:
    """Aggregates multi-timeframe market signals and emits regime state."""

    def __init__(
        self,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        volatility_analyzer: Optional[VolatilityAnalyzer] = None,
        liquidity_analyzer: Optional[LiquidityAnalyzer] = None,
        classifier: Optional[RegimeClassifier] = None,
        timeframe_weights: Optional[Dict[str, float]] = None,
    ):
        self.trend_analyzer = trend_analyzer or TrendAnalyzer()
        self.volatility_analyzer = volatility_analyzer or VolatilityAnalyzer()
        self.liquidity_analyzer = liquidity_analyzer or LiquidityAnalyzer()
        self.classifier = classifier or RegimeClassifier()
        self.timeframe_weights = timeframe_weights or {"5m": 1.0, "15m": 1.2, "1h": 1.4, "1d": 1.8}
        self._listeners: List[Callable[[Dict], None]] = []
        self._state: Dict = {
            "regime": "RANGE_BOUND",
            "confidence": 0.0,
            "timestamp": None,
            "details": {},
        }

    def detect_regime(self, timeframe_data: Dict[str, Dict], extra_signals: Optional[Dict] = None) -> Dict:
        """Detect regime from multi-timeframe input data.

        Args:
            timeframe_data: mapping, e.g. {"5m": {...}, "1h": {...}}
            extra_signals: optional global signals (market breadth, vix, etc.)
        """
        extra_signals = extra_signals or {}
        if not timeframe_data:
            return self.get_regime_state()

        per_tf = {}
        votes = {}
        weighted_conf = 0.0
        weight_sum = 0.0

        for tf, data in timeframe_data.items():
            trend = self.trend_analyzer.analyze(data)
            vol = self.volatility_analyzer.analyze(data)
            liq = self.liquidity_analyzer.analyze(data)
            cls = self.classifier.classify(trend=trend, volatility=vol, liquidity=liq, extra=extra_signals)

            weight = float(self.timeframe_weights.get(tf, 1.0))
            per_tf[tf] = {
                "trend": trend,
                "volatility": vol,
                "liquidity": liq,
                "classification": cls,
                "weight": weight,
            }
            regime = cls["regime"]
            votes[regime] = votes.get(regime, 0.0) + weight
            weighted_conf += weight * float(cls.get("confidence", 0.0))
            weight_sum += weight

        final_regime = max(votes.keys(), key=lambda key: votes[key])
        confidence = (weighted_conf / weight_sum) if weight_sum > 0 else 0.0

        self._state = {
            "regime": final_regime,
            "confidence": round(confidence, 4),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "details": per_tf,
        }
        return self._state

    def get_regime_state(self) -> Dict:
        return dict(self._state)

    def register_listener(self, callback: Callable[[Dict], None]) -> None:
        if callable(callback):
            self._listeners.append(callback)

    def broadcast_regime(self, payload: Optional[Dict] = None, strategy_bank_layer=None, autonomous_controller=None) -> Dict:
        """Broadcast regime to listeners and optional injected integrations."""
        data = payload or self.get_regime_state()

        if strategy_bank_layer and hasattr(strategy_bank_layer, "is_enabled") and strategy_bank_layer.is_enabled():
            # Keep update non-invasive: strategy layer may use this signal externally.
            rows = strategy_bank_layer.registry_rows()
            for row in rows:
                row.setdefault("last_regime", data.get("regime"))

        if autonomous_controller is not None and hasattr(autonomous_controller, "mode"):
            # Expose regime hint for autonomous policy decisions.
            setattr(autonomous_controller, "last_regime", data.get("regime"))

        for callback in self._listeners:
            try:
                callback(data)
            except Exception:
                continue

        return data
