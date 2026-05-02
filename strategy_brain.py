import random

class StrategyBrain:

    def __init__(self, indicators):
        self.indicators = indicators

    def trend_strategy(self, symbol):
        price = self.indicators.get_price(symbol)
        sma = self.indicators.get_sma(symbol, 20)
        rsi = self.indicators.get_rsi(symbol)

        if price > sma and rsi > 55:
            return {"side": "BUY", "confidence": 0.7}

        if price < sma and rsi < 45:
            return {"side": "SELL", "confidence": 0.7}

        return None

    def mean_reversion(self, symbol):
        rsi = self.indicators.get_rsi(symbol)

        if rsi < 30:
            return {"side": "BUY", "confidence": 0.6}

        if rsi > 70:
            return {"side": "SELL", "confidence": 0.6}

        return None

    def breakout(self, symbol):
        price = self.indicators.get_price(symbol)
        high = self.indicators.get_high(symbol, 20)
        low = self.indicators.get_low(symbol, 20)

        if price is None or high is None or low is None:
            return None

        if price > high:
            return {"side": "BUY", "confidence": 0.8}

        if price < low:
            return {"side": "SELL", "confidence": 0.8}

        return None

    def decide(self, symbol):
        signals = []

        for strat in [
            self.trend_strategy,
            self.mean_reversion,
            self.breakout
        ]:
            sig = strat(symbol)
            if sig:
                signals.append(sig)

        if not signals:
            return None

        # 🧠 voting
        buy_score = sum(s["confidence"] for s in signals if s["side"] == "BUY")
        sell_score = sum(s["confidence"] for s in signals if s["side"] == "SELL")

        if buy_score > sell_score:
            side = "BUY"
            strength = buy_score
        else:
            side = "SELL"
            strength = sell_score

        return {
            "symbol": symbol,
            "side": side,
            "strength": strength
        }