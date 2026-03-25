import yfinance as yf
import pandas as pd
from datetime import datetime

WATCHLIST = [
    "TATASTEEL.NS",
    "HDFCBANK.NS",
    "ADANIENT.NS",
    "SBIN.NS",
    "RELIANCE.NS"
]

# ==============================
# SAFE FLOAT
# ==============================

def f(x):
    try:
        if hasattr(x, "iloc"):
            return float(x.iloc[-1])
        return float(x)
    except:
        return 0


# ==============================
# MARKET ANALYSIS
# ==============================

def analyze(df):

    close = df["Close"]

    ema20 = f(close.ewm(span=20).mean())
    ema50 = f(close.ewm(span=50).mean())

    atr = f((df["High"] - df["Low"]).rolling(14).mean())

    vol = f(df["Volume"])
    vol_avg = f(df["Volume"].rolling(20).mean())

    price = f(close)

    trend_strength = abs(ema20 - ema50) / price if price != 0 else 0
    volatility = atr / price if price != 0 else 0
    participation = vol / vol_avg if vol_avg != 0 else 0

    return trend_strength, volatility, participation


# ==============================
# STRATEGY SCORER
# ==============================

def strategy_score(trend, vol, part):

    scores = {}

    # EMA Pullback Strategy
    scores["EMA_PULLBACK"] = trend * part

    # ORB Scalping Strategy
    scores["ORB_SCALP"] = vol * part

    # Momentum Strategy
    scores["CONFIDENCE_MOMENTUM"] = trend * vol * part

    return scores


# ==============================
# TRADE TYPE DECIDER
# ==============================

def trade_type(trend, vol):

    if trend > 0.007:
        return "FUTURES_INTRADAY"

    if vol > 0.003:
        return "SCALPING"

    return "SWING_PREP"


# ==============================
# MAIN DESK SCORER
# ==============================

def desk():

    print("\n===== STRATEGY CONFIDENCE SCORER =====\n")

    results = {}

    for sym in WATCHLIST:

        try:
            df = yf.download(sym, period="5d", interval="5m")

            if df.empty:
                continue

            trend, vol, part = analyze(df)

            strat_scores = strategy_score(trend, vol, part)

            best_strategy = max(strat_scores, key=strat_scores.get)

            confidence = strat_scores[best_strategy]

            ttype = trade_type(trend, vol)

            results[sym] = (confidence, best_strategy, ttype)

        except:
            continue

    if not results:
        print("❌ No market data")
        return

    leader = max(results, key=lambda x: results[x][0])

    conf, strat, ttype = results[leader]

    print("🔥 Leader:", leader)
    print("🎯 Strategy:", strat)
    print("🧠 Trade Type:", ttype)
    print("💎 Confidence:", round(conf, 5))

    if conf < 0.003:
        print("\n❌ Trade Avoid — Weak Opportunity")
    else:
        print("\n✅ Deploy Strategy in Bulls AI")


if __name__ == "__main__":
    desk()