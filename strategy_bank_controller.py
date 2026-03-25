import os
import importlib
import yfinance as yf
import pandas as pd
from datetime import datetime

STRATEGY_FOLDER = "strategy_bank"

WATCHLIST = [
    "TATASTEEL.NS",
    "HDFCBANK.NS",
    "ADANIENT.NS",
    "SBIN.NS",
    "^NSEBANK",
    "^NSEI"
]

# ======================================
# MARKET REGIME DETECTOR
# ======================================

def market_regime(df):

    close = df["Close"]

    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]

    atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]
    vol = df["Volume"].iloc[-1]
    vol_avg = df["Volume"].rolling(20).mean().iloc[-1]

    trend = abs(ema20 - ema50) / close.iloc[-1]
    volatility = atr / close.iloc[-1]
    participation = vol / vol_avg if vol_avg != 0 else 0

    if trend > 0.006 and participation > 1.2:
        return "TREND"

    if volatility > 0.003:
        return "SCALP"

    return "RANGE"


# ======================================
# INSTRUMENT RANKER
# ======================================

def rank_instruments():

    scores = {}

    for symbol in WATCHLIST:

        try:
            df = yf.download(symbol, period="5d", interval="5m")

            if df.empty:
                continue

            regime = market_regime(df)

            close = df["Close"]
            ema20 = close.ewm(span=20).mean().iloc[-1]
            ema50 = close.ewm(span=50).mean().iloc[-1]

            trend = abs(ema20 - ema50) / close.iloc[-1]

            scores[symbol] = trend

        except:
            continue

    if not scores:
        return None, None

    leader = max(scores, key=scores.get)

    return leader, scores


# ======================================
# STRATEGY SELECTOR
# ======================================

def choose_strategy(regime):

    if regime == "TREND":
        return "confidence_momentum"

    if regime == "SCALP":
        return "orb_scalp"

    return "ema_pullback"


# ======================================
# MAIN DESK DECISION
# ======================================

def desk_decision():

    print("\n===== STRATEGY BANK CONTROLLER =====\n")

    leader, ranking = rank_instruments()

    if leader is None:
        print("❌ No market data")
        return

    df = yf.download(leader, period="5d", interval="5m")

    regime = market_regime(df)

    strategy = choose_strategy(regime)

    print("🔥 Leader Instrument:", leader)
    print("📊 Market Regime:", regime)
    print("🧠 Deploy Strategy:", strategy)

    print("\n👉 ACTION:")
    print("Paste strategy:", strategy)
    print("Use Instrument:", leader)
    print("Lot Mode: FULL")


if __name__ == "__main__":
    desk_decision()