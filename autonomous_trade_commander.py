import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# ================================
# CONFIG
# ================================

WATCHLIST = [
    "^NSEBANK",
    "^NSEI",
    "TATASTEEL.NS",
    "ADANIENT.NS",
    "SBIN.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "RELIANCE.NS"
]

# ================================
# VOLATILITY ENGINE
# ================================

def market_volatility(symbol="^NSEBANK"):

    df = yf.download(symbol, period="3d", interval="5m", progress=False)

    atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]
    price = df["Close"].iloc[-1]

    vol = float(atr) / float(price)

    return vol

# ================================
# EXPIRY ENGINE
# ================================

def expiry_detector():

    today = datetime.now().date()

    # NSE index expiry Thursday logic
    weekday = today.weekday()

    if weekday == 3:
        return "EXPIRY"

    if weekday == 2:
        return "PRE_EXPIRY"

    return "NORMAL"

# ================================
# INSTRUMENT SCREENER
# ================================

def screener():

    results = {}

    for symbol in WATCHLIST:

        try:

            df = yf.download(symbol, period="5d", interval="15m", progress=False)

            ema20 = df["Close"].ewm(span=20).mean().iloc[-1]
            ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
            atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]
            price = df["Close"].iloc[-1]

            trend_strength = abs(float(ema20) - float(ema50)) / float(price)
            volatility = float(atr) / float(price)

            score = trend_strength * volatility

            results[symbol] = score

        except:
            pass

    ranking = sorted(results.items(), key=lambda x: x[1], reverse=True)

    return ranking

# ================================
# TRADE PERMISSION ENGINE
# ================================

def trade_permission():

    vol = market_volatility()
    expiry = expiry_detector()
    ranking = screener()

    best_symbol = ranking[0][0]
    best_score = ranking[0][1]

    print("\n==============================")
    print(" AUTONOMOUS DESK COMMANDER ")
    print("==============================")

    print("\n📊 Market Volatility:", round(vol,5))
    print("📅 Expiry Status:", expiry)

    print("\n🔥 Instrument Ranking")
    for sym, sc in ranking:
        print(sym, round(sc,5))

    print("\n⭐ Best Battlefield:", best_symbol)

    # ===== DECISION TREE =====

    if vol < 0.002:
        decision = "❌ NO TRADE DAY"

    elif expiry == "EXPIRY":
        decision = "⚠️ TRADE VERY SMALL SIZE (INDEX SPIKE DAY)"

    elif vol > 0.004:
        decision = "🔥 FULL MOMENTUM DAY → TRADE INDEX"

    else:
        decision = "✅ SELECTIVE DAY → TRADE TOP STOCK FUTURE"

    print("\n🎯 FINAL DESK DECISION:", decision)

# ================================
# RUN
# ================================

if __name__ == "__main__":
    trade_permission()