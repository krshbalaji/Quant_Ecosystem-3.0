import requests
import yfinance as yf


# =========================
# 🔍 SEARCH ENGINE (NO HARDCODE)
# =========================
def search_instrument(query):
    import yfinance as yf

    try:
        query = query.upper()

        # Try NSE format first
        ticker = yf.Ticker(query + ".NS")
        data = ticker.history(period="1d")

        if not data.empty:
            return [{
                "symbol": query,
                "exchange": "NSE"
            }]

        # Try raw symbol (fallback)
        ticker = yf.Ticker(query)
        data = ticker.history(period="1d")

        if not data.empty:
            return [{
                "symbol": query,
                "exchange": "GLOBAL"
            }]

        return []

    except Exception as e:
        print("Search error:", e)
        return []

# =========================
# 📊 LIVE PRICE + VOLUME
# =========================
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d")

        if hist.empty:
            return None

        latest = hist.iloc[-1]

        return {
            "price": float(latest["Close"]),
            "volume": int(latest["Volume"])
        }

    except Exception as e:
        print(f"Data error: {e}")
        return None


# =========================
# 🌍 INDIA VIX (LIVE)
# =========================
def get_vix():
    try:
        vix = yf.Ticker("^INDIAVIX")
        data = vix.history(period="1d")

        if data.empty:
            return 17  # fallback

        return float(data["Close"].iloc[-1])

    except:
        return 17


# =========================
# 📊 MARKET SENTIMENT (PCR PROXY)
# =========================
def get_market_sentiment():
    """
    Proxy logic (until full NSE option chain added)
    """
    try:
        nifty = yf.Ticker("^NSEI")
        data = nifty.history(period="5d")

        change = data["Close"].pct_change().iloc[-1]

        if change > 0.01:
            return "BULLISH"
        elif change < -0.01:
            return "BEARISH"
        else:
            return "SIDEWAYS"

    except:
        return "UNKNOWN"