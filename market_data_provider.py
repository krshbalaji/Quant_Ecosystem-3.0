import yfinance as yf
import pandas as pd
import time

class MarketDataProvider:

    def __init__(self):
        self.cache = {}
        self.base_ttl = 10

    def _safe_float(self, val):
        if isinstance(val, pd.Series):
            val = val.iloc[-1]
        if hasattr(val, "item"):
            val = val.item()
        return float(val)

    def get_data(self, symbol, retries=2):

        # ---- CACHE ----
        now = time.time()
        if symbol in self.cache:
            data, ts = self.cache[symbol]
            if now - ts < self.base_ttl:
                print(f"[CACHE HIT] {symbol}")
                return data

        for attempt in range(retries):
            try:
                print(f"[FETCH] {symbol}")

                df = yf.download(symbol, period="1d", interval="1m", progress=False)

                if df is None or df.empty:
                    print(f"[DATA EMPTY] {symbol}")
                    return None

                close_val = df["Close"].iloc[-1]
                high_val  = df["High"].iloc[-1]
                low_val   = df["Low"].iloc[-1]

                price = self._safe_float(close_val)
                high  = self._safe_float(high_val)
                low   = self._safe_float(low_val)

                # ATR
                df["H-L"] = df["High"] - df["Low"]
                df["H-PC"] = (df["High"] - df["Close"].shift(1)).abs()
                df["L-PC"] = (df["Low"] - df["Close"].shift(1)).abs()

                tr = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
                atr_val = tr.rolling(14).mean().iloc[-1]

                atr = self._safe_float(atr_val) if not pd.isna(atr_val) else 0.0

                if any(pd.isna(x) for x in [price, high, low]):
                    return None

                data = {
                    "price": price,
                    "high": high,
                    "low": low,
                    "atr": atr
                }

                self.cache[symbol] = (data, now)
                return data

            except Exception as e:
                print(f"[RETRY {attempt+1}] {symbol}: {e}")
                time.sleep(1)

        print(f"[FAILED DATA] {symbol}")
        return None


provider = MarketDataProvider()