import yfinance as yf
import numpy as np


def regime_tf(symbol , interval):

    df = yf.download(symbol , period="10d" , interval=interval , progress=False)

    close = df["Close"]

    ema20 = close.ewm(span=20).mean()
    ema50 = close.ewm(span=50).mean()

    slope = (ema20.iloc[-1] - ema20.iloc[-5]) / close.iloc[-1]

    if abs(slope) < 0.001:
        return "RANGE"

    if abs(slope) < 0.003:
        return "TREND_BUILD"

    return "STRONG_TREND"


def multi_tf_regime(symbol):

    r5 = regime_tf(symbol , "5m")
    r15 = regime_tf(symbol , "15m")
    r1h = regime_tf(symbol , "60m")

    print("\n===== MULTI TF REGIME =====\n")
    print("5m →", r5)
    print("15m →", r15)
    print("1h →", r1h)

    score = 0

    if r5 == "STRONG_TREND":
        score += 1
    if r15 == "STRONG_TREND":
        score += 2
    if r1h == "STRONG_TREND":
        score += 3

    print("\nTrend Score:", score)

    if score >= 4:
        print("🔥 Institutional Trend Alignment")
    else:
        print("⚠️ Mixed Market")


multi_tf_regime("^NSEBANK")