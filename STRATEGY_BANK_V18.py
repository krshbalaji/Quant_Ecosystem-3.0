import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ================================
# MARKET PHYSICS ENGINE
# ================================

def candle_strength(df):
    body = abs(df["Close"] - df["Open"])
    range_ = df["High"] - df["Low"]
    return float((body / range_).iloc[-1])


def trend_angle(df):
    ema = df["Close"].ewm(span=20).mean()
    angle = (ema.iloc[-1] - ema.iloc[-5]) / df["Close"].iloc[-1]
    return float(angle)


def volatility_regime(df):
    atr = (df["High"] - df["Low"]).rolling(14).mean()
    vol = atr.iloc[-1] / df["Close"].iloc[-1]
    return float(vol)


def participation(df):
    vol = df["Volume"].iloc[-1]
    avg = df["Volume"].rolling(20).mean().iloc[-1]
    if avg == 0:
        return 0
    return float(vol / avg)


# ================================
# REGIME CLASSIFIER
# ================================

def classify_regime(df):

    angle = trend_angle(df)
    vol = volatility_regime(df)
    part = participation(df)

    if vol < 0.001:
        return "DEAD"

    if angle < 0.0015:
        return "RANGE"

    if angle < 0.003:
        return "TREND_BUILD"

    return "STRONG_TREND"


# ================================
# STRATEGY BANK
# ================================

def select_strategy(regime):

    if regime == "DEAD":
        return "NO_TRADE"

    if regime == "RANGE":
        return "VWAP_SCALP"

    if regime == "TREND_BUILD":
        return "EMA_PULLBACK"

    if regime == "STRONG_TREND":
        return "BREAKOUT_PYRAMID"


# ================================
# CAPITAL BEHAVIOUR ENGINE
# ================================

def capital_mode(regime):

    if regime == "DEAD":
        return 0 , "NONE"

    if regime == "RANGE":
        return 25 , "HALF"

    if regime == "TREND_BUILD":
        return 50 , "NORMAL"

    if regime == "STRONG_TREND":
        return 100 , "AGGRESSIVE"


# ================================
# INSTRUMENT RANKER
# ================================

symbols = [
    "^NSEBANK",
    "^NSEI",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
    "TATASTEEL.NS",
    "ADANIENT.NS"
]


def rank_instruments():

    ranking = {}

    for s in symbols:
        try:
            df = yf.download(s, period="5d", interval="5m", progress=False)
            if len(df) < 50:
                continue

            score = abs(trend_angle(df)) * participation(df)
            ranking[s] = score

        except:
            pass

    leader = max(ranking, key=ranking.get)

    return leader , ranking


# ================================
# DESK MASTER
# ================================

def desk_master():

    print("\n===== AUTONOMOUS STRATEGY BANK V18 =====\n")

    leader , ranking = rank_instruments()

    df = yf.download(leader, period="5d", interval="5m", progress=False)

    regime = classify_regime(df)

    strategy = select_strategy(regime)

    capital , mode = capital_mode(regime)

    price = df["Close"].iloc[-1]

    print("🔥 Leader:", leader)
    print("📊 Regime:", regime)
    print("🧠 Strategy:", strategy)
    print("💰 Capital %:", capital)
    print("⚡ Lot Mode:", mode)
    print("📍 Price:", round(price,2))

    if regime == "DEAD":
        print("\n❌ TRADE BLOCKED → DEAD MARKET")
    else:
        print("\n✅ READY → Deploy Strategy in Bulls AI")


desk_master()

def bullsai_strategy_generator(strategy):

    print("\n===== BULLS AI DEPLOYMENT PLAN =====\n")

    if strategy == "VWAP_SCALP":

        print("Use Strategy → VWAP Range Scalper")
        print("Timeframe → 5m")
        print("SL → 0.25%")
        print("Target → 0.4%")
        print("Entry → VWAP rejection")

    elif strategy == "EMA_PULLBACK":

        print("Use Strategy → EMA Pullback Momentum")
        print("Timeframe → 5m")
        print("SL → EMA50 break")
        print("Target → 1R / trail")

    elif strategy == "BREAKOUT_PYRAMID":

        print("Use Strategy → Opening Range Breakout")
        print("Timeframe → 5m")
        print("SL → Range Low")
        print("Target → Pyramid Trail")

    else:
        print("No Deployment Today")


# Modify desk_master end

    bullsai_strategy_generator(strategy)