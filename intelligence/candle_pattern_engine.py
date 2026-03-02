class CandlePatternEngine:

    def detect(self, candle):

        patterns = []

        body = abs(candle["close"] - candle["open"])
        range_ = candle["high"] - candle["low"]

        if body / range_ < 0.2:
            patterns.append("DOJI")

        if candle["close"] > candle["open"]:
            patterns.append("BULLISH")

        return patterns