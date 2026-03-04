import random
import time
from collections import defaultdict, deque

class MarketDataEngine:
    """
    Central market data distributor for Quant Ecosystem.
    """

    def __init__(self, broker, symbols=None, timeframe="5m", history=500):

            self._series = {}
            self._rng = random.Random()
            self.broker = broker
            self.symbols = symbols or []
            self.timeframe = timeframe
            self.history_size = history

            self.data = defaultdict(lambda: {
                "open": deque(maxlen=history),
                "high": deque(maxlen=history),
                "low": deque(maxlen=history),
                "close": deque(maxlen=history),
                "volume": deque(maxlen=history)
            })

            self.listeners = []

            self.last_update = None
            self.running = False

    def register_listener(self, callback):
        """
        Engines subscribe to market data updates
        """
        if callable(callback):
            self.listeners.append(callback)

    async def start(self):

        self.running = True
        print("MarketDataEngine started")

        while self.running:

            try:

                await self.fetch_market_data()

                payload = self.get_snapshot()

                for listener in self.listeners:
                    try:
                        listener(payload)
                    except Exception as e:
                        print("MarketData listener error:", e)

            except Exception as e:
                print("MarketDataEngine error:", e)

            await asyncio.sleep(2)

    async def fetch_market_data(self):

        if not self.symbols:
            return

        try:

            candles = self.broker.get_candles(
                symbols=self.symbols,
                timeframe=self.timeframe
            )

        except Exception as e:

            print("Market data fetch failed:", e)
            return

        if not candles:
            return

        for symbol, c in candles.items():

            d = self.data[symbol]

            d["open"].append(c["open"])
            d["high"].append(c["high"])
            d["low"].append(c["low"])
            d["close"].append(c["close"])
            d["volume"].append(c["volume"])

        self.last_update = time.time()

    def get_snapshot(self):

        snapshot = {}

        for symbol, d in self.data.items():

            snapshot[symbol] = {
                "open": list(d["open"]),
                "high": list(d["high"]),
                "low": list(d["low"]),
                "close": list(d["close"]),
                "volume": list(d["volume"]),
            }
        
        return snapshot

    def stop(self):
        self.running = False
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
