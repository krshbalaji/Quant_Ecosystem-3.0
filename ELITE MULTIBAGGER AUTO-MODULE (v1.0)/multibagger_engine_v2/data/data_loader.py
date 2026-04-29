import yfinance as yf

# You can expand this list dynamically later (NSE fetch)
NSE_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "LT.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "BAJFINANCE.NS",
    "KEI.NS"
]


def load_data():
    stocks = []

    for symbol in NSE_SYMBOLS:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            stocks.append({
                "symbol": symbol.replace(".NS", ""),
                "price": info.get("currentPrice", 0),
                "pe": info.get("trailingPE", 0) or 0,
                "pb": info.get("priceToBook", 0) or 0,
                "roe": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0,
                "debt_equity": info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else 0,
                "promoter_holding": 50,  # placeholder until NSE data
                "revenue_growth": 15,
                "profit_growth": 15,
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
                "high_52w": info.get("fiftyTwoWeekHigh", 0),
                "capex_growth": 20
            })

        except Exception as e:
            print(f"Error loading {symbol}: {e}")

    return stocks