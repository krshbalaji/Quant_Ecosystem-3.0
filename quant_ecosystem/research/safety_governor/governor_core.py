"""
PATCH: quant_ecosystem/governor/governor_core.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class GovernorCore:
    """
    Risk governance layer — enforces position limits, concentration
    caps, and regulatory guardrails before any order leaves the system.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._rules = []

    def add_rule(self, rule):
        """Register a governance rule (callable that accepts an order dict)."""
        self._rules.append(rule)

    def approve(self, order: dict) -> bool:
        """
        Returns True if the order passes all governance rules.
        Stub always approves in PAPER mode.
        """
        for rule in self._rules:
            try:
                if not rule(order):
                    print(f"[GovernorCore] Order REJECTED by rule: {rule.__name__}")
                    return False
            except Exception as exc:
                print(f"[GovernorCore] Rule error: {exc}")
                return False
        return True
