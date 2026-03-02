class RegimeDetector:

    def detect(self, volatility, trend):
        if volatility >= 2.8:
            return "CRISIS"

        if volatility >= 1.8:
            return "HIGH_VOLATILITY"

        if volatility <= 0.3:
            return "LOW_VOLATILITY"

        if trend > 0:
            return "TREND"

        if trend < 0:
            return "MEAN_REVERSION"

        return "MEAN_REVERSION"
