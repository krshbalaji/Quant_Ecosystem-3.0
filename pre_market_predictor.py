import yfinance as yf
import pandas as pd
import datetime

SYMBOL = "^NSEBANK"

def safe(x):
    try:
        import pandas as pd

        if isinstance(x, pd.DataFrame):
            return float(x.values[-1][0])

        if isinstance(x, pd.Series):
            return float(x.iloc[-1])

        return float(x)

    except:
        return 0.0

def get_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)
    return df

def compute_gap(df):
    prev_close = float(df["Close"].iloc[-2])
    open_price = float(df["Open"].iloc[-1])
    return abs(open_price - prev_close) / prev_close

def compute_volatility(df):
    atr = (df["High"] - df["Low"]).rolling(14).mean()
    return safe(atr) / safe(df["Close"])

def compute_trend_strength(df):
    ema20 = df["Close"].ewm(span=20).mean()
    ema50 = df["Close"].ewm(span=50).mean()
    return abs(safe(ema20) - safe(ema50)) / safe(df["Close"])

def previous_day_bias(df):

    try:
        last_close = float(df["Close"].iloc[-1].item())
        prev_close = float(df["Close"].iloc[-20].item())
    except:
        return "UNKNOWN"

    if last_close > prev_close:
        return "BULL"
    else:
        return "BEAR"

def predict_day_type():

    df = get_data(SYMBOL)

    gap = compute_gap(df)
    vol = compute_volatility(df)
    trend = compute_trend_strength(df)

    trend_prob = 0
    range_prob = 0
    trap_prob = 0

    if gap > 0.004:
        trend_prob += 40
        trap_prob += 20
    else:
        range_prob += 40

    if vol < 0.002:
        trend_prob += 30
    else:
        range_prob += 20

    if trend > 0.002:
        trend_prob += 30
    else:
        range_prob += 30

    if trend_prob > range_prob:
        return "TREND"
    elif range_prob > trend_prob:
        return "RANGE"
    else:
        return "TRAP"

    # -------- PROBABILITY ENGINE -------- #

    trend_prob = 0
    range_prob = 0
    trap_prob = 0

    # GAP BASED
    if gap > 0.004:
        trend_prob += 40
        trap_prob += 20
    else:
        range_prob += 40

    # VOLATILITY
    if vol < 0.002:
        trend_prob += 30
    else:
        range_prob += 20

    # TREND STRUCTURE
    if trend > 0.002:
        trend_prob += 30
    else:
        range_prob += 30

    # NORMALIZE
    total = trend_prob + range_prob + trap_prob

    trend_prob = int((trend_prob / total) * 100)
    range_prob = int((range_prob / total) * 100)
    trap_prob = int((trap_prob / total) * 100)

    # -------- OUTPUT -------- #

    print("📊 Gap:", round(gap,4))
    print("📊 Volatility:", round(vol,4))
    print("📊 Trend Strength:", round(trend,4))
    print("🧠 Prev Bias:", bias)

    print("\n🔮 DAY PROBABILITY")

    print("Trend Day →", trend_prob, "%")
    print("Range Day →", range_prob, "%")
    print("Trap Day →", trap_prob, "%")

    # -------- FINAL CALL -------- #

    if trend_prob > 60:
        print("\n🔥 EXPECT TREND DAY")
    elif range_prob > 60:
        print("\n⚠️ EXPECT RANGE DAY")
    else:
        print("\n🧨 HIGH TRAP PROBABILITY")

if __name__ == "__main__":
    predict_day_type()