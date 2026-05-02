import yfinance as yf
import pandas as pd
import time


class IndicatorAdapter:

    def __init__(self):
        self.cache = {}
        self.last_fetch = {}
        self.cache_ttl = 10  # seconds

    def get_data(self, symbol):
        now = time.time()

        if symbol in self.cache:
            if now - self.last_fetch[symbol] < self.cache_ttl:
                return self.cache[symbol]

        data = yf.download(
            symbol,
            period="60d",
            interval="1d",
            progress=False,
            auto_adjust=True
        )

        if data.empty:
            return None

        self.cache[symbol] = data
        self.last_fetch[symbol] = now

        return data

    def get_price(self, symbol):
        data = self.get_data(symbol)
        if data is None:
            return None

        return float(data["Close"].iloc[-1].item())

    def get_high(self, symbol, period=20):
        data = self.get_data(symbol)
        if data is None:
            return None

        return float(data["High"].tail(period).max().item())

    def get_low(self, symbol, period=20):
        data = self.get_data(symbol)
        if data is None:
            return None

        return float(data["Low"].tail(period).min().item())

    def get_sma(self, symbol, period=20):
        data = self.get_data(symbol)
        if data is None:
            return None

        return float(data["Close"].rolling(period).mean().iloc[-1].item())

    def get_rsi(self, symbol, period=14):
        data = self.get_data(symbol)
        if data is None:
            return None

        delta = data["Close"].diff()

        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1].item())

    def get_atr(self, symbol, period=14):
        data = self.get_data(symbol)
        if data is None:
            return None

        high = data["High"]
        low = data["Low"]
        close = data["Close"]

        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()

        return float(atr.iloc[-1])    