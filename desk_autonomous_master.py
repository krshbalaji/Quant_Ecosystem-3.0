import yfinance as yf
import pandas as pd
import datetime as dt
import numpy as np


symbols = [
    "^NSEBANK",
    "^NSEI",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
    "TATASTEEL.NS",
    "ADANIENT.NS"
]


# ================= SAFE VALUE =================

def safe(x):
    if isinstance(x, pd.Series):
        return float(x.iloc[-1])
    if isinstance(x, pd.DataFrame):
        return float(x.iloc[-1,0])
    return float(x)


# ================= MARKET REGIME =================

def regime(df):

    close = df["Close"]

    ema20 = close.ewm(span=20).mean()
    ema50 = close.ewm(span=50).mean()

    trend_strength = abs(safe(ema20) - safe(ema50)) / safe(close)

    atr = safe((df["High"] - df["Low"]).rolling(14).mean()) / safe(close)

    vol_now = safe(df["Volume"])
    vol_avg = safe(df["Volume"].rolling(20).mean())

    participation = vol_now / vol_avg if vol_avg != 0 else 0

    if trend_strength > 0.004:
        day = "TREND"
    elif atr < 0.001:
        day = "DEAD"
    else:
        day = "RANGE"

    return day, trend_strength, atr, participation


# ================= INSTRUMENT RANK =================

def rank():

    scores = {}

    for s in symbols:

        try:
            df = yf.download(s, period="5d", interval="5m", progress=False)

            if len(df) < 50:
                continue

            day, trend, atr, part = regime(df)

            score = trend * part * atr
            scores[s] = score

        except:
            continue

    if not scores:
        return None, {}

    leader = max(scores, key=scores.get)

    return leader, scores


# ================= TIME ENGINE =================

def phase():

    now = dt.datetime.now().time()

    if now < dt.time(9,15):
        return "PRE"

    if now < dt.time(9,35):
        return "NOISE"

    if now < dt.time(12,15):
        return "ACTIVE"

    if now < dt.time(13,30):
        return "LUNCH"

    if now < dt.time(15,10):
        return "POWER"

    return "CLOSED"


# ================= STRATEGY SELECTOR =================

def strategy(day, participation):

    if day == "TREND" and participation > 1.2:
        return "EMA_PULLBACK"

    if day == "RANGE":
        return "ORB_SCALP"

    if day == "DEAD":
        return "NO_TRADE"

    return "LIGHT_MOMENTUM"


# ================= CAPITAL COMMAND =================

def capital_plan(atr, participation):

    if atr < 0.0015:
        return 0, "NONE"

    if participation > 1.5:
        return 100, "FULL"

    if participation > 1.2:
        return 50, "HALF"

    return 25, "LIGHT"


# ================= MASTER DESK =================

def desk():

    print("\n===== AUTONOMOUS DESK MASTER =====\n")

    leader, scores = rank()

    if leader is None:
        print("❌ No market data")
        return

    df = yf.download(leader, period="5d", interval="5m", progress=False)

    day, trend, atr, part = regime(df)

    strat = strategy(day, part)

    cap, mode = capital_plan(atr, part)

    ph = phase()

    print("🔥 Leader:", leader)
    print("📊 Day Type:", day)
    print("📈 Participation:", round(part,2))
    print("🧠 Strategy:", strat)
    print("💰 Capital %:", cap)
    print("⚡ Lot Mode:", mode)
    print("🕒 Phase:", ph)

    if ph in ["NOISE","LUNCH","CLOSED","PRE"]:
        print("\n❌ TRADE BLOCKED BY TIME ENGINE")
        return

    if strat == "NO_TRADE":
        print("\n❌ TRADE BLOCKED BY REGIME")
        return

    if cap == 0:
        print("\n❌ TRADE BLOCKED BY VOLATILITY")
        return

    print("\n✅ DEPLOY IN BULLS AI")


if __name__ == "__main__":
    desk()