"""
PATCH: quant_ecosystem/intelligence/global_intelligence_engine.py
FIX:   BUG #2 — Replaced self-owned MarketDataEngine instantiation with None.
       MarketDataEngine MUST be injected by SystemRouter, not created here.
"""


class GlobalIntelligenceEngine:
    """
    Aggregates macro signals and cross-asset intelligence.

    `market_data` is intentionally None on construction.
    SystemRouter is responsible for calling:
        engine.market_data = <MarketDataEngine instance>
    after the engine graph is wired.
    """

class GlobalIntelligenceEngine:

    def __init__(self):

        self.market_data = None

        # ---------------------------------------------------------------
        # PATCHED: was `self.market_data = MarketDataEngine()`
        # That line caused a second MarketDataEngine to be spun up inside
        # GlobalIntelligenceEngine, bypassing SystemRouter wiring entirely.
        # MarketDataEngine is now injected externally.
        # ---------------------------------------------------------------
        

    # ------------------------------------------------------------------
    # Injection point (called by SystemRouter after the graph is built)
    # ------------------------------------------------------------------

    def set_market_data(self, engine):
        self.market_data = engine

    # ------------------------------------------------------------------
    # Core interface stubs
    # ------------------------------------------------------------------

    def analyze(self):
        """Run global intelligence pass (stub)."""
        if self.market_data is None:
            print("[GlobalIntelligenceEngine] WARNING: market_data not injected yet.")
        return {}

    def get_macro_signal(self):
        return None
