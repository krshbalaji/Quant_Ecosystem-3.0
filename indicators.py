import requests
import numpy as np

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_ohlc(symbol, range_="3mo", interval="1d"):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_}&interval={interval}"

        res = requests.get(url, headers=HEADERS, timeout=5)

        if res.status_code != 200:
            print(f"[DATA ERROR] {symbol}: status {res.status_code}")
            return None, None, None

        data = res.json()

        if "chart" not in data or not data["chart"]["result"]:
            print(f"[DATA ERROR] {symbol}: empty result")
            return None, None, None

        q = data["chart"]["result"][0]["indicators"]["quote"][0]

        close = np.array(clean_series(q["close"]), dtype=float)
        high  = np.array(clean_series(q["high"]), dtype=float)
        low = np.array(clean_series(q["low"]), dtype=float)

        # ensure minimum length
        if len(close) < 20:
            print(f"[DATA WARNING] {symbol}: low data ({len(close)})")
            
        return close, high, low

    except Exception as e:
        print(f"[DATA ERROR] {symbol}: {e}")
        return None, None, None

    for _ in range(2):
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            data = res.json()
            break
        except:
            continue

def sma(series, n):
    if len(series) < n:
        return None
    return np.array([np.mean(series[i-n:i]) for i in range(n, len(series)+1)])


def rsi(close, period=14):
    if len(close) < period + 1:
        return None
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period]) + 1e-9

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(high, low, close, period=14):
    if len(close) < period + 1:
        return None
    trs = []
    for i in range(1, len(close)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )
        trs.append(tr)
    return np.mean(trs[-period:])

def fetch_multi_tf(symbol):
    # Daily trend
    daily_close, daily_high, daily_low = fetch_ohlc(symbol, "3mo", "1d")

    # Intraday momentum (1h)
    intraday_close, _, _ = fetch_ohlc(symbol, "5d", "60m")

    return {
        "daily": (daily_close, daily_high, daily_low),
        "intraday": intraday_close
    }   

def clean_series(arr):
    clean = []
    last = None

    for x in arr:
        if x is not None:
            clean.append(x)
            last = x
        else:
            clean.append(last if last is not None else 0)

    return clean     