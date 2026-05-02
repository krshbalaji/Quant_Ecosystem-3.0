import time
import requests
import os

from indicator_adapter import IndicatorAdapter
from strategy_brain import StrategyBrain

URL = "https://quant-ecosystem-shadow-16683273546.asia-south1.run.app"
API_KEY = os.getenv("CLOUD_API_KEY")

HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY
}

indicators = IndicatorAdapter()
brain = StrategyBrain(indicators)

SYMBOLS = ["TCS.NS", "RELIANCE.NS"]
SCAN_INTERVAL = 30

last_signal_time = {}
COOLDOWN = 30


def send_signal(signal):
    payload = {
        "symbol": signal["symbol"],
        "side": signal["side"],
        "qty": 1,
        "strength": signal["strength"]
    }

    try:
        r = requests.post(f"{URL}/signal", headers=HEADERS, json=payload)

        if r.status_code == 200:
            print("📡 SIGNAL SENT:", payload)
        else:
            print("❌ Rejected:", r.text)

    except Exception as e:
        print("Cloud error:", e)


print("🧠 Multi-Strategy Brain Started...")

print("API KEY:", API_KEY)

while True:
    for symbol in SYMBOLS:

        sig = brain.decide(symbol)

        if not sig:
            continue

        now = time.time()

        if symbol in last_signal_time:
            if now - last_signal_time[symbol] < COOLDOWN:
                continue

        last_signal_time[symbol] = now

        print("📊 Decision:", sig)
        send_signal(sig)

    time.sleep(SCAN_INTERVAL)