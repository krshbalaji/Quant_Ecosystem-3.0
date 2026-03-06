"""
PATCH: quant_ecosystem/allocation/allocation_engine.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class AllocationEngine:
    """
    Computes capital allocation weights across strategies/assets.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config

    def allocate(self, signals: dict) -> dict:
        """Return weight map from signals (stub — equal weight)."""
        if not signals:
            return {}
        weight = 1.0 / len(signals)
        return {k: weight for k in signals}
