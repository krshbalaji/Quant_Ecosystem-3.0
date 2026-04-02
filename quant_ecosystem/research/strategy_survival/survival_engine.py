"""
PATCH: quant_ecosystem/survival/survival_engine.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class SurvivalEngine:
    """
    Risk-of-ruin guard — halts trading when drawdown limits are breached.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._halt = False

    def evaluate(self, equity_curve: list) -> bool:
        """
        Returns True if trading should continue, False if survival threshold
        has been breached (stub — always safe in PAPER mode).
        """
        return not self._halt

    def halt(self):
        """Force a survival halt."""
        self._halt = True
        print("[SurvivalEngine] HALT triggered.")

    def resume(self):
        self._halt = False
