import yfinance as yf
import pandas as pd
import datetime

UNIVERSE = [
    "^NSEBANK",
    "^NSEI",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
    "TATASTEEL.NS",
    "ADANIENT.NS"
]

# ---------------- SAFE LAST ---------------- #

def last(x):
    if isinstance(x, pd.Series):
        return float(x.iloc[-1])
    if isinstance(x, pd.DataFrame):
        return float(x.values[-1][0])
    return float(x)

# ---------------- MULTI TF BIAS ---------------- #

def mtf_bias(symbol):

    try:
        df15 = yf.download(symbol, period="5d", interval="15m", progress=False)
        df1h = yf.download(symbol, period="10d", interval="60m", progress=False)

        if len(df15) < 50 or len(df1h) < 50:
            return "UNKNOWN"

        ema_fast_15 = last(df15["Close"].ewm(span=20).mean())
        ema_slow_15 = last(df15["Close"].ewm(span=50).mean())

        ema_fast_1h = last(df1h["Close"].ewm(span=20).mean())
        ema_slow_1h = last(df1h["Close"].ewm(span=50).mean())

        if ema_fast_15 > ema_slow_15 and ema_fast_1h > ema_slow_1h:
            return "BULL"

        if ema_fast_15 < ema_slow_15 and ema_fast_1h < ema_slow_1h:
            return "BEAR"

        return "MIXED"

    except:
        return "UNKNOWN"

# ---------------- REGIME ---------------- #

def regime(df):

    close = df["Close"]

    ema20 = last(close.ewm(span=20).mean())
    ema50 = last(close.ewm(span=50).mean())

    strength = abs(ema20 - ema50) / last(close)

    vol = last(df["Volume"])
    vol_avg = last(df["Volume"].rolling(20).mean())

    participation = vol / vol_avg if vol_avg != 0 else 0

    if strength > 0.003 and participation > 1.2:
        return "TREND"

    if strength < 0.0015:
        return "RANGE"

    return "MIXED"

# ---------------- SCORE ---------------- #

def score(df):

    close = df["Close"]

    ema20 = last(close.ewm(span=20).mean())
    ema50 = last(close.ewm(span=50).mean())

    atr = last((df["High"] - df["Low"]).rolling(14).mean())
    price = last(close)

    if price == 0:
        return 0

    trend_component = abs(ema20 - ema50) / price
    volatility_component = atr / price

    return trend_component * volatility_component

# ---------------- CAPITAL PLAN ---------------- #

def capital_plan(conviction):

    if conviction > 0.02:
        return 100, "FULL"

    if conviction > 0.01:
        return 70, "THREE-FOURTH"

    if conviction > 0.005:
        return 40, "HALF"

    return 0, "NONE"

# ---------------- RANK ---------------- #

def rank_market():

    ranking = {}

    for s in UNIVERSE:

        try:
            print("Checking", s)

            df = yf.download(
                s,
                period="5d",
                interval="5m",
                progress=False
            )

            if df is None or len(df) < 60:
                continue

            ranking[s] = score(df)

        except:
            pass

    if not ranking:
        return None, None

    leader = max(ranking, key=ranking.get)

    return leader, ranking

# ---------------- COMMANDER ---------------- #

def commander():

    print("\n===== INSTITUTIONAL DEPLOYMENT COMMANDER V5 =====\n")

    leader, ranking = rank_market()

    if leader is None:
        print("❌ No Data")
        return

    df = yf.download(leader, period="5d", interval="5m", progress=False)

    reg = regime(df)
    bias = mtf_bias(leader)
    conviction = ranking[leader]

    capital_pct, lot_mode = capital_plan(conviction)

    price = last(df["Close"])

    print("\n🔥 Leader:", leader)
    print("📊 Regime:", reg)
    print("🧠 MultiTF Bias:", bias)
    print("💎 Conviction:", round(conviction,5))
    print("💰 Price:", round(price,2))

    print("\n💰 CAPITAL PLAN")
    print("Use Capital →", capital_pct, "%")
    print("Lot Mode →", lot_mode)

    # FINAL STRATEGY DECISION

    if capital_pct == 0:
        print("\n❌ NO TRADE TODAY")
        return

    if reg == "TREND":

        if "^" in leader:
            print("\n🎯 Strategy → EMA_PULLBACK FUTURES INDEX")

        else:
            print("\n🎯 Strategy → MOMENTUM STOCK FUTURES")

    elif reg == "RANGE":

        print("\n🎯 Strategy → ORB_SCALP OPTIONS")

    else:
        print("\n❌ EDGE NOT CLEAR → STAY OUT")

if __name__ == "__main__":
    commander()