import logging

from quant_ecosystem.regime_ai.regime_ai_core import RegimeAICore
from quant_ecosystem.regime_ai.feature_engineer import FeatureEngineer
from quant_ecosystem.regime_ai.regime_classifier import RegimeClassifier

from quant_ecosystem.regime_transition.transition_detector import RegimeTransitionDetector

logger = logging.getLogger(__name__)


class RegimeIntelligenceEngine:
    """
    Adapter layer combining:
    - Feature engineering
    - Regime classification
    - Transition detection
    """

    def __init__(self, **kwargs):

        self.feature_engineer = FeatureEngineer()
        self.classifier = RegimeClassifier()
        self.core = RegimeAICore()

        self.transition_detector = RegimeTransitionDetector()

        self.current_regime = "UNKNOWN"

        logger.info("RegimeIntelligenceEngine initialized")

    def update(self, market_snapshot, extra_signals=None):
        """
        Update regime detection from market data
        """

        features = self.feature_engineer.build_feature_vector(
            market_snapshot,
            extra_signals=extra_signals,
        )

        normalized = self.feature_engineer.normalize_features(features)

        vector = self.feature_engineer.as_ordered_vector(normalized)

        regime = self.classifier.predict_regime(vector)

        self.current_regime = regime

        return regime

    def detect_transition(self, timeframe_data):

        state = self.transition_detector.detect_transition(
            timeframe_data,
            current_regime=self.current_regime,
        )

        return state

    def get_regime(self):
        return self.current_regime