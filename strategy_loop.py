import time
import requests
import os
from datetime import datetime

# 🔴 Use your existing ecosystem
from indicator_adapter import IndicatorAdapter
from position_sizer import PositionSizer

sizer = PositionSizer(capital=100000, risk_per_trade=0.01)

URL = "https://quant-ecosystem-shadow-16683273546.asia-south1.run.app"
API_KEY = os.getenv("CLOUD_API_KEY")

if not API_KEY:
    raise ValueError("CLOUD_API_KEY not set")

HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY
}

indicators = IndicatorAdapter()

# ===== CONFIG =====
SYMBOLS = ["NIFTY", "RELIANCE.NS"]
SCAN_INTERVAL = 10  # seconds


# ===== STRATEGY LOGIC =====
def generate_signal(symbol):
    try:
        price = indicators.get_price(symbol)
        rsi = indicators.get_rsi(symbol)
        sma = indicators.get_sma(symbol, period=20)

        price = indicators.get_price(symbol)
        atr = indicators.get_atr(symbol)

        stop_loss = price - atr

        qty = sizer.size(price, stop_loss)

        # 🧠 Simple intelligent logic
        if price > sma and rsi > 55:
            return {
                "symbol": symbol,
                "side": "BUY",
                "qty": qty
            }

        if price < sma and rsi < 45:
            return {
                "symbol": symbol,
                "side": "SELL",
                "qty": qty
            }

        return None

    except Exception as e:
        print(f"Indicator error for {symbol}:", e)
        return None


# ===== SEND TO CLOUD =====
def send_signal(signal):
    try:
        r = requests.post(
            f"{URL}/signal",
            headers=HEADERS,
            json=signal,
            timeout=10
        )

        if r.status_code == 200:
            print("📡 SIGNAL SENT:", signal)
        else:
            print("❌ Signal rejected:", r.text)

    except Exception as e:
        print("Cloud error:", e)


# ===== MAIN LOOP =====
print("🧠 Strategy loop started...")

while True:
    try:
        for symbol in SYMBOLS:
            sig = generate_signal(symbol)

            if sig:
                print("📊 Generated:", sig)
                send_signal(sig)

        time.sleep(SCAN_INTERVAL)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(5)