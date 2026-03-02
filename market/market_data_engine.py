import random
from collections import deque


class MarketDataEngine:

    def __init__(self):
        self._series = {}
        self._rng = random.Random()

    def ensure_symbol(self, symbol, seed_price=None):
        if symbol in self._series:
            return

        base = float(seed_price or self._rng.uniform(100, 1000))
        history = deque(maxlen=200)
        for _ in range(100):
            base *= 1 + self._rng.uniform(-0.003, 0.003)
            history.append(round(base, 4))
        self._series[symbol] = history

    def update_tick(self, symbol):
        self.ensure_symbol(symbol)
        history = self._series[symbol]
        last = history[-1]
        next_price = last * (1 + self._rng.uniform(-0.004, 0.004))
        history.append(round(next_price, 4))
        return history[-1]

    def get_price(self, symbol):
        self.ensure_symbol(symbol)
        return self._series[symbol][-1]

    def get_close_series(self, symbol, lookback=50):
        self.ensure_symbol(symbol)
        history = list(self._series[symbol])
        return history[-lookback:]

    def get_snapshot(self, symbol, lookback=50):
        price = self.update_tick(symbol)
        closes = self.get_close_series(symbol, lookback=lookback)
        volatility = self._compute_volatility(closes)
        trend = self._compute_trend(closes)
        return {
            "symbol": symbol,
            "price": price,
            "close": closes,
            "volatility": volatility,
            "trend": trend,
        }

    def get_volatility(self):
        symbol = "NSE:NIFTY50-INDEX"
        snapshot = self.get_snapshot(symbol=symbol, lookback=40)
        return snapshot["volatility"]

    def get_trend(self):
        symbol = "NSE:NIFTY50-INDEX"
        snapshot = self.get_snapshot(symbol=symbol, lookback=40)
        return snapshot["trend"]

    def _compute_volatility(self, closes):
        if len(closes) < 2:
            return 1.0

        returns = []
        for index in range(1, len(closes)):
            prev = closes[index - 1]
            cur = closes[index]
            if prev == 0:
                continue
            returns.append((cur - prev) / prev)

        if not returns:
            return 1.0

        mean_return = sum(returns) / len(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
        std_dev = variance ** 0.5
        return max(std_dev * 100, 0.01)

    def _compute_trend(self, closes):
        if len(closes) < 5:
            return 0

        short = sum(closes[-5:]) / 5
        long = sum(closes[-20:]) / min(len(closes), 20)

        if short > long * 1.001:
            return 1
        if short < long * 0.999:
            return -1
        return 0
