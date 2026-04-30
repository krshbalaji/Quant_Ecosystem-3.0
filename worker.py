import time
import requests
import os
import json
import hashlib
from datetime import datetime, UTC

# ✅ USE YOUR SYSTEM
from quant_ecosystem.broker.broker_router import BrokerRouter
from quant_ecosystem.portfolio.portfolio_engine import PortfolioEngine
from quant_ecosystem.risk_engine.portfolio_risk_manager import PortfolioRiskManager
from indicator_adapter import IndicatorAdapter

URL = "https://quant-ecosystem-shadow-16683273546.asia-south1.run.app"
API_KEY = os.getenv("CLOUD_API_KEY")

if not API_KEY:
    raise ValueError("CLOUD_API_KEY not set")

HEADERS = {"X-API-KEY": API_KEY}

SEEN_FILE = "seen_ids.json"

broker = BrokerRouter()
portfolio = PortfolioEngine()
risk = PortfolioRiskManager()
indicators = IndicatorAdapter()

MAX_LOSS = -2000


# ===== UTIL =====
def sig_id(sig):
    raw = f"{sig.get('symbol')}|{sig.get('side')}|{sig.get('qty')}"
    return hashlib.sha1(raw.encode()).hexdigest()


def load_json(path, default):
    try:
        return json.load(open(path))
    except:
        return default


def save_json(path, obj):
    json.dump(obj, open(path, "w"), indent=2)


# ===== EXIT SYSTEM (USING YOUR PORTFOLIO) =====
def check_exit():
    positions = portfolio.get_positions()

    for sym, pos in positions.items():
        if pos["qty"] <= 0:
            continue

        live = indicators.get_price(sym)

        if live <= pos.get("stop_loss", 0) or live >= pos.get("take_profit", float("inf")):
            print(f"🚪 EXIT {sym}")

            broker.route_order({
                "symbol": sym,
                "qty": pos["qty"],
                "side": "SELL"
            })

            portfolio.close_position(sym)


# ===== MAIN =====
seen = set(load_json(SEEN_FILE, []))

print("🚀 Worker connected to Quant Ecosystem...")

while True:
    try:
        # 🔴 GLOBAL RISK
        pnl = portfolio.get_total_pnl()

        if pnl < MAX_LOSS:
            print("🚨 GLOBAL LOSS LIMIT HIT")
            requests.post(f"{URL}/kill-switch", headers=HEADERS, json={"enabled": True})
            time.sleep(5)
            continue

        # 🔴 EXIT SYSTEM
        check_exit()

        # 🔽 SIGNAL
        r = requests.get(f"{URL}/latest-signal", headers=HEADERS, timeout=10)

        if r.status_code != 200:
            time.sleep(2)
            continue

        sig = r.json()

        if not sig or not sig.get("symbol"):
            time.sleep(2)
            continue

        sid = sig_id(sig)

        if sid in seen:
            time.sleep(2)
            continue

        sym = sig["symbol"]
        qty = int(sig["qty"])

        # 🔴 PORTFOLIO CHECK
        if portfolio.has_position(sym):
            print(f"⚠️ Already holding {sym}")
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

        # 🔴 RISK ENGINE (your system)
        if not risk.validate_trade(sig):
            print("RISK BLOCKED")
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

        price = indicators.get_price(sym)

        # 🔴 DYNAMIC SL/TP using your indicator system
        atr = indicators.get_atr(sym)

        stop_loss = price - atr
        take_profit = price + (2 * atr)

        order = {
            "symbol": sym,
            "qty": qty,
            "side": "BUY",
            "price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ts": datetime.now(UTC).isoformat()
        }

        broker.route_order(order)

        portfolio.add_position(order)

        print("ENTRY:", order)

        seen.add(sid)
        save_json(SEEN_FILE, list(seen))

    except Exception as e:
        print("ERROR:", str(e))

    time.sleep(2)