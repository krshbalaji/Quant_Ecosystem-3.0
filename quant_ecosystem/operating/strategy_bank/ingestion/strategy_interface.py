class Strategy:

    SUPPORTED_REGIMES = ["TREND", "MEAN_REVERSION", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS"]

    def generate_signal(self, data, regime, context):
        return {"side": "HOLD", "confidence": 0.0}
