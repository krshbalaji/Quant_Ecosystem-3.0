"""
PATCH: quant_ecosystem/strategy/selector_core.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class SelectorCore:
    """
    Selects the optimal strategy for current market regime.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config

    def select(self, regime, candidates):
        """Return best strategy from candidates given the regime (stub)."""
        return candidates[0] if candidates else None
