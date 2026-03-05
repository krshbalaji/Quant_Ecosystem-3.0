import pandas as pd

class EMATrendStrategy:

    id = "ema_trend"

    def generate_signal(self, candles):

        if not candles or len(candles) < 50:
            return None

        df = pd.DataFrame(candles)

        df["ema_fast"] = df["close"].ewm(span=20).mean()
        df["ema_slow"] = df["close"].ewm(span=50).mean()

        if df["ema_fast"].iloc[-1] > df["ema_slow"].iloc[-1]:
            return "BUY"

        if df["ema_fast"].iloc[-1] < df["ema_slow"].iloc[-1]:
            return "SELL"

        return None