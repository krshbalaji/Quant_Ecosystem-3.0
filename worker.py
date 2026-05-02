import time
import requests
import os
import json
import hashlib
from datetime import datetime, UTC

from quant_ecosystem.broker.paper_broker import PaperBroker
from quant_ecosystem.broker.broker_router import BrokerRouter
from indicator_adapter import IndicatorAdapter
from position_engine import add_position, remove_position, get_positions
from risk_engine import check_risk
from position_sizer import calculate_qty
from portfolio_brain import PortfolioBrain

portfolio = PortfolioBrain(capital=100000)

URL = "https://quant-ecosystem-shadow-16683273546.asia-south1.run.app"
API_KEY = os.getenv("CLOUD_API_KEY")

if not API_KEY:
    raise ValueError("CLOUD_API_KEY not set")

HEADERS = {"X-API-KEY": API_KEY}
SEEN_FILE = "seen_ids.json"

broker = BrokerRouter(PaperBroker())
indicators = IndicatorAdapter()

MAX_LOSS = -2000


def sig_id(sig):
    raw = f"{sig.get('symbol')}|{sig.get('side')}"
    return hashlib.sha1(raw.encode()).hexdigest()
    raw = f"{symbol}|{side}|{sig.get('ts')}"

def load_json(path, default):
    try:
        return json.load(open(path))
    except:
        return default


def save_json(path, obj):
    json.dump(obj, open(path, "w"), indent=2)


def check_exit():
    positions = get_positions()

    for sym, pos in positions.items():
        if "side" not in pos:
            pos["side"] = "BUY"  # assume legacy long
        
        qty = pos["qty"]

        live = indicators.get_price(sym)

        side = pos.get("side", "BUY")  # fallback safety

        if side == "BUY":
            if live <= pos["stop_loss"] or live >= pos["take_profit"]:
                broker.place_order(sym, "SELL", qty)
                remove_position(sym)

        elif side == "SELL":
            if live >= pos["stop_loss"] or live <= pos["take_profit"]:
                broker.place_order(sym, "BUY", qty)
                remove_position(sym)
           
seen = set(load_json(SEEN_FILE, []))

print("🚀 Worker connected to Quant Ecosystem...")

while True:
    try:
        # 🔴 Global PnL check
        positions = get_positions()
        pnl = 0

        for sym, pos in positions.items():
            live = indicators.get_price(sym)
            pnl += (live - pos["entry_price"]) * pos["qty"]

        if pnl < MAX_LOSS:
            print("🚨 Global loss hit")
            requests.post(f"{URL}/kill-switch", headers=HEADERS, json={"enabled": True})
            time.sleep(5)
            continue

        # 🔴 Exit
        check_exit()

        # 🔽 Get signal
        r = requests.get(f"{URL}/status", headers=HEADERS, timeout=10)

        if r.status_code != 200:
            time.sleep(2)
            continue

        data = r.json()
        sig = data.get("last_signal")

        if not sig or not sig.get("symbol"):
            time.sleep(2)
            continue

        sid = sig_id(sig)

        if sid in seen:
            time.sleep(2)
            continue

        # ✅ mark immediately (IMPORTANT)
        
        sym = sig["symbol"]

        

        # 🔴 Risk check
        ok, reason = check_risk(sig)

        if not ok:
            print("RISK BLOCKED:", reason)
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

                # === GET MARKET DATA ===
        side = sig.get("side", "BUY")

        price = indicators.get_price(sym)
        atr = indicators.get_atr(sym)

        if price is None or atr is None:
            continue

        # === BUILD SL / TP ===
        if side == "BUY":
            stop_loss = price - atr * 1.5
            take_profit = price + atr * 3
        else:
            stop_loss = price + atr * 1.5
            take_profit = price - atr * 3

        # === PORTFOLIO CHECK ===
        if not portfolio.can_take_trade(positions, sym):
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

        # === POSITION SIZE ===
        qty = portfolio.calculate_position_size(price, stop_loss)

        strength = sig.get("strength", 1)
        qty = int(qty * strength)

        if qty < 1:
            qty = 1

        # 🔴 Skip if already holding
        positions = get_positions()
        if sym in positions:
            seen.add(sid)
            save_json(SEEN_FILE, list(seen))
            continue

        # === EXECUTION ===
        print(f"🧪 PAPER ORDER: {side} {sym} x{qty}")

        order = {
            "symbol": sym,
            "qty": qty,
            "side": side,
            "price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ts": datetime.now(UTC).isoformat()
        }

        print("ENTRY:", order)

        broker.place_order(sym, side, qty)
        add_position(order)

        seen.add(sid)
        save_json(SEEN_FILE, list(seen))

        print("ENTRY:", order)
        
    except Exception as e:
        print("ERROR:", str(e))

    time.sleep(2)