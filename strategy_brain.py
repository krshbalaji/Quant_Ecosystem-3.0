import random
from indicators import fetch_multi_tf, sma, rsi, atr


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

        data = fetch_multi_tf(symbol)

        if not data:
            return None

        close, high, low = data["daily"]
        intraday = data["intraday"]

        if close is None or intraday is None:
            return None

        # --- DAILY TREND
        sma20 = sma(close, 20)
        sma50 = sma(close, 50)

        if sma20 is None or sma50 is None:
            return None

        trend_up = sma20[-1] > sma50[-1]
        trend_down = sma20[-1] < sma50[-1]

        # --- INTRADAY MOMENTUM
        r_intraday = rsi(intraday)

        if r_intraday is None:
            return None

        momentum_buy = r_intraday > 55
        momentum_sell = r_intraday < 45

        # --- BREAKOUT LOGIC
        recent_high = max(close[-10:])
        recent_low = min(close[-10:])

        price = close[-1]

        breakout_up = price >= recent_high
        breakout_down = price <= recent_low

        # --- VOLATILITY FILTER
        a = atr(high, low, close)
        volatility_ok = a and a > (0.004 * price)

        # --- SIDEWAYS FILTER
        if price <= 0:
            return None


        range_pct = (recent_high - recent_low) / price

        sideways = range_pct < 0.02  # tight range

        # --- SCORING
        score = 0

        if trend_up and momentum_buy:
            score += 1

        if trend_down and momentum_sell:
            score += 1

        if breakout_up or breakout_down:
            score += 0.7

        if volatility_ok:
            score += 0.5

        if sideways:
            score -= 1  # avoid chop

        # --- FINAL DECISION
        if score >= 1:
            side = "BUY" if trend_up else "SELL"

            return {
                "symbol": symbol,
                "side": side,
                "strength": round(score, 2)
            }

        # fallback
        if trend_up:
            return {"symbol": symbol, "side": "BUY", "strength": 0.3}

        if trend_down:
            return {"symbol": symbol, "side": "SELL", "strength": 0.3}

        return None