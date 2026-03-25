import yfinance as yf

SYMBOL = "^NSEBANK"


def f(x):
    try:
        return float(x.iloc[-1])
    except:
        return 0


def classify():

    print("\n===== MARKET DAY CLASSIFIER =====\n")

    df = yf.download(SYMBOL, period="5d", interval="5m")

    if df.empty:
        print("❌ No data")
        return

    close = df["Close"]

    ema20 = f(close.ewm(span=20).mean())
    ema50 = f(close.ewm(span=50).mean())

    atr = f((df["High"] - df["Low"]).rolling(14).mean())
    price = f(close)

    participation = f(df["Volume"]) / f(df["Volume"].rolling(20).mean())

    trend = abs(ema20 - ema50) / price
    volatility = atr / price

    print("Trend Strength:", round(trend,5))
    print("Volatility:", round(volatility,5))
    print("Participation:", round(participation,2))

    if volatility < 0.0018:
        print("\n❌ DEAD DAY → Avoid Intraday")

    elif trend > 0.008 and participation > 1.3:
        print("\n🔥 TREND DAY → Deploy Momentum / Futures")

    elif volatility > 0.003:
        print("\n⚡ BREAKOUT DAY → Deploy ORB / Scalping")

    else:
        print("\n📊 RANGE DAY → Deploy Mean Reversion")


if __name__ == "__main__":
    classify()