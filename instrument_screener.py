import yfinance as yf

symbols = [
    "^NSEI",
    "^NSEBANK",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "TATASTEEL.NS",
    "ADANIENT.NS"
]

def score_symbol(sym):

    try:
        df = yf.download(sym, period="5d", interval="5m", progress=False)

        if df is None or len(df) < 60:
            return None

        close = df["Close"]

        ema20 = float(close.ewm(span=20).mean().iloc[-1])
        ema50 = float(close.ewm(span=50).mean().iloc[-1])
        atr = float((df["High"] - df["Low"]).rolling(14).mean().iloc[-1])

        last_price = close.iloc[-1]

        trend_strength = abs(float(ema20) - float(ema50)) / float(last_price)
        volatility = float(atr) / float(last_price)

        score = trend_strength * 0.7 + volatility * 0.3

        return float(score)

    except Exception as e:
        print(f"Skip {sym}")
        return None


results = {}

for s in symbols:
    sc = score_symbol(s)
    if sc is not None:
        results[s] = sc

ranking = sorted(results.items(), key=lambda x: x[1], reverse=True)

print("\n🔥 Intraday Instrument Ranking\n")

for sym, sc in ranking:
    print(sym, round(sc, 5))

if ranking:
    print("\n👉 Suggested Instrument:", ranking[0][0])
else:
    print("\n❌ No instrument found")