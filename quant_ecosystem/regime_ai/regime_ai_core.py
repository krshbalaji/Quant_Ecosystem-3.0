"""
PATCH: quant_ecosystem/regime/regime_ai_core.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class RegimeAICore:
    """
    Classifies the current market regime (trending, mean-reverting,
    volatile, etc.) using ML-based or rule-based heuristics.
    """

    REGIMES = ("trending", "mean_reverting", "volatile", "unknown")

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._current_regime = "unknown"

    def classify(self, features: dict) -> str:
        """
        Classify the regime from a feature dict.
        Stub returns 'unknown' until the model is wired.
        """
        return self._current_regime

    def get_regime(self) -> str:
        return self._current_regime
