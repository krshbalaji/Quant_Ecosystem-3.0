"""Market intelligence micro-layer adapter."""

from intelligence.global_intelligence_engine import GlobalIntelligenceEngine


class MarketIntelligenceLayer:
    """Independent intelligence facade used by institutional controller."""

    def __init__(self, engine=None):
        self.engine = engine or GlobalIntelligenceEngine()

    def collect(self):
        report = self.engine.analyze()
        return {
            "price": report.get("price_proxy", 0.0),
            "volume": report.get("volume_proxy", 0.0),
            "options_chain": report.get("options_chain_proxy", {}),
            "volatility_regime": report.get("regime_advanced", report.get("regime", "RANGING")),
            "raw": report,
        }
