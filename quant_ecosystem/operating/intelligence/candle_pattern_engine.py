class CandlePatternEngine:

    def detect(self, candle):
        patterns = []

        body = abs(candle["close"] - candle["open"])
        range_ = candle["high"] - candle["low"]
        if range_ <= 0:
            return patterns

        if body / range_ < 0.2:
            patterns.append("DOJI")

        if candle["close"] > candle["open"] and body / range_ > 0.6:
            patterns.append("BULL_ENGULF")
        if candle["close"] < candle["open"] and body / range_ > 0.6:
            patterns.append("BEAR_ENGULF")

        if candle["close"] > candle["open"]:
            patterns.append("BULLISH")
        elif candle["close"] < candle["open"]:
            patterns.append("BEARISH")

        return patterns
