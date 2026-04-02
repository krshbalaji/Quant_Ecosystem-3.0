"""
PATCH: quant_ecosystem/pulse/pulse_engine.py
FIX:   Constructor now accepts config=None, **kwargs.
"""


class PulseEngine:
    """
    Monitors system health and market micro-structure pulse
    (latency, fill rates, spread widening, etc.).
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._metrics = {}

    def record(self, key: str, value):
        self._metrics[key] = value

    def get(self, key: str):
        return self._metrics.get(key)

    def health_check(self) -> bool:
        """Returns True if all monitored metrics are within normal range (stub)."""
        return True
