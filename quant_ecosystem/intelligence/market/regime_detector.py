class RegimeDetector:

    def detect(self, volatility, trend):
        advanced = self.detect_advanced(volatility=volatility, trend=trend)
        mapping = {
            "PANIC": "CRISIS",
            "BREAKOUT": "TREND",
            "TRENDING_UP": "TREND",
            "TRENDING_DOWN": "MEAN_REVERSION",
            "RANGE": "MEAN_REVERSION",
            "HIGH_VOLATILITY": "HIGH_VOLATILITY",
            "LOW_VOLATILITY": "LOW_VOLATILITY",
        }
        return mapping.get(advanced, "MEAN_REVERSION")

    def detect_advanced(self, volatility, trend):
        if volatility >= 2.8:
            return "PANIC"
        if volatility >= 1.8 and abs(float(trend)) > 0:
            return "BREAKOUT"
        if volatility >= 1.8:
            return "HIGH_VOLATILITY"
        if volatility <= 0.3:
            return "LOW_VOLATILITY"
        if trend > 0:
            return "TRENDING_UP"
        if trend < 0:
            return "TRENDING_DOWN"
        return "RANGE"
