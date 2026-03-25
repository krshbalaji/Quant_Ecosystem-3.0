import yfinance as yf

symbol = "^NSEBANK"

df = yf.download(symbol, period="3d", interval="5m", progress=False)

atr_series = (df["High"] - df["Low"]).rolling(14).mean()
price_series = df["Close"]

atr = float(atr_series.iloc[-1].iloc[0] if hasattr(atr_series.iloc[-1], "iloc") else atr_series.iloc[-1])
price = float(price_series.iloc[-1].iloc[0] if hasattr(price_series.iloc[-1], "iloc") else price_series.iloc[-1])

volatility = atr / price

print("\n📊 Market Volatility:", round(volatility,5))

if volatility > 0.004:
    print("🔥 HIGH MOVEMENT DAY → Full Intraday Trading Allowed")

elif volatility > 0.002:
    print("⚠️ Moderate Day → Trade Carefully (Max 3 trades)")

else:
    print("❌ Low Movement → Avoid Intraday Algo Today")