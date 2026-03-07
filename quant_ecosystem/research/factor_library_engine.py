import pandas as pd
import numpy as np


class FactorLibraryEngine:

    def __init__(self, **kwargs):
        pass

    # ------------------------------
    # Momentum Factors
    # ------------------------------

    def momentum(self, close, window=20):
        return close.pct_change(window)

    def rsi(self, close, period=14):

        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss

        return 100 - (100 / (1 + rs))

    # ------------------------------
    # Mean Reversion
    # ------------------------------

    def zscore(self, series, window=20):

        mean = series.rolling(window).mean()
        std = series.rolling(window).std()

        return (series - mean) / std

    def bollinger_position(self, close, window=20):

        mean = close.rolling(window).mean()
        std = close.rolling(window).std()

        upper = mean + 2 * std
        lower = mean - 2 * std

        return (close - lower) / (upper - lower)

    # ------------------------------
    # Volatility
    # ------------------------------

    def volatility(self, close, window=20):

        returns = close.pct_change()

        return returns.rolling(window).std()

    def atr(self, high, low, close, window=14):

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        return tr.rolling(window).mean()

    # ------------------------------
    # Volume Factors
    # ------------------------------

    def volume_spike(self, volume, window=20):

        mean_vol = volume.rolling(window).mean()

        return volume / mean_vol

    # ------------------------------
    # Trend
    # ------------------------------

    def moving_average(self, close, window=50):

        return close.rolling(window).mean()

    def ema(self, close, window=20):

        return close.ewm(span=window).mean()

    # ------------------------------
    # Master factor generator
    # ------------------------------

    def generate_all_factors(self, df):

        factors = pd.DataFrame(index=df.index)

        factors["momentum"] = self.momentum(df["close"])

        factors["rsi"] = self.rsi(df["close"])

        factors["zscore"] = self.zscore(df["close"])

        factors["bollinger_pos"] = self.bollinger_position(df["close"])

        factors["volatility"] = self.volatility(df["close"])

        factors["atr"] = self.atr(df["high"], df["low"], df["close"])

        factors["volume_spike"] = self.volume_spike(df["volume"])

        factors["ma50"] = self.moving_average(df["close"], 50)

        factors["ema20"] = self.ema(df["close"], 20)

        return factors