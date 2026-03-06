"""
PATCH: quant_ecosystem/allocation/diversity_engine.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class DiversityEngine:
    """
    Enforces portfolio diversity constraints.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config

    def check(self, portfolio: dict) -> bool:
        """Validate diversity constraints on a portfolio (stub — always passes)."""
        return True

    def rebalance(self, portfolio: dict) -> dict:
        """Return a rebalanced portfolio dict (stub — passthrough)."""
        return portfolio
