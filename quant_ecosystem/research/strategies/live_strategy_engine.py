"""
PATCH: quant_ecosystem/strategy/live_strategy_engine.py
FIX:   Constructor now accepts config=None, **kwargs so SystemFactory can
       inject config without a TypeError.
"""


class LiveStrategyEngine:
    """
    Executes live (or paper) strategy signals in real-time.
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self._running = False

    def start(self):
        mode = (self.config or {}).get("mode", "PAPER")
        print(f"[LiveStrategyEngine] Starting in {mode} mode.")
        self._running = True

    def stop(self):
        self._running = False

    def on_signal(self, signal):
        """Process an inbound strategy signal (stub)."""
        pass
