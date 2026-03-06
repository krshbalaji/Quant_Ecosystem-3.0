"""
PATCH: quant_ecosystem/market/market_data_engine.py
FIX:   BUG #1 — Removed recursive self-instantiation.
       MarketDataEngine must NEVER create another MarketDataEngine.
       MarketDataEngine is injected by SystemRouter where needed.
"""


class MarketDataEngine:
    """
    Provides market data feed management.

    Constructor accepts `config` and `universe` so SystemFactory can inject
    them via:
        MarketDataEngine(config=self._config, universe=universe)

    self.market_data has been REMOVED — it caused infinite recursion.
    """

    def __init__(self, config=None, universe=None):
        self.config = config
        self.universe = universe
        self.feed = None

    # ------------------------------------------------------------------
    # Public interface (stubs — flesh out in domain layer as needed)
    # ------------------------------------------------------------------

    def start(self):
        """Activate the market data feed."""
        print("[MarketDataEngine] Starting feed...")

    def stop(self):
        """Deactivate the market data feed."""
        print("[MarketDataEngine] Stopping feed...")

    def get_price(self, symbol: str):
        """Return latest price for symbol (stub returns None in PAPER mode)."""
        return None

    def get_universe(self):
        """Return the active trading universe."""
        return self.universe or []
