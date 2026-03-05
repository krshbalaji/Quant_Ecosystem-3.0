from collections import defaultdict, deque

class MarketCache:

    def __init__(self, history=500):
        self.cache = defaultdict(lambda: deque(maxlen=history))

    def update(self, symbol, candle):
        self.cache[symbol].append(candle)

    def get_series(self, symbol):
        return list(self.cache.get(symbol, []))

    def get_latest(self, symbol):
        if symbol in self.cache and self.cache[symbol]:
            return self.cache[symbol][-1]
        return None