"""
Global intelligence engine.
MarketDataEngine is injected externally by SystemFactory/SystemRouter.
"""

class GlobalIntelligenceEngine:
    """
    Aggregates macro signals and cross-asset intelligence.

    market_data is intentionally None on construction.
    SystemFactory wires it after engine graph is built:
        router.global_intelligence.set_market_data(router.market_data)
    """

    def __init__(self, config=None, **kwargs):
        self.config = config
        self.market_data = None

    def set_market_data(self, engine):
        """Inject MarketDataEngine after the engine graph is wired."""
        self.market_data = engine

    def analyze(self):
        if self.market_data is None:
            print("[GlobalIntelligenceEngine] WARNING: market_data not injected yet.")
        return {}

    def get_macro_signal(self):
        return None