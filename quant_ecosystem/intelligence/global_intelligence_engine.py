"""
PATCH: quant_ecosystem/intelligence/global_intelligence_engine.py
<<<<<<< Updated upstream
FIX:   BUG #2 — Replaced self-owned MarketDataEngine instantiation with None.
       MarketDataEngine MUST be injected by SystemRouter, not created here.
=======
FIX 1: Duplicate class definition removed.
FIX 2: Constructor now accepts config=None, **kwargs (SystemFactory compatibility).
FIX 3: Removed internal MarketDataEngine instantiation (recursion prevention).
       market_data is injected externally via set_market_data().
>>>>>>> Stashed changes
"""


class GlobalIntelligenceEngine:
    """
    Aggregates macro signals and cross-asset intelligence.
<<<<<<< Updated upstream

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
=======

    market_data is intentionally None on construction.
    SystemFactory wires it after the full engine graph is built:
        router.global_intelligence.set_market_data(router.market_data)
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        # PATCHED: was self.market_data = MarketDataEngine()
        # That caused a second MarketDataEngine inside GlobalIntelligenceEngine,
        # bypassing SystemRouter wiring. Injected externally now.
        self.market_data = None

    def set_market_data(self, engine):
        """Inject MarketDataEngine after the engine graph is wired."""
        self.market_data = engine

    def analyze(self):
>>>>>>> Stashed changes
        if self.market_data is None:
            print("[GlobalIntelligenceEngine] WARNING: market_data not injected yet.")
        return {}

    def get_macro_signal(self):
        return None
