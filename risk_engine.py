import json
import os

RISK_CONFIG = {
    "max_trade_qty": 5,
    "max_daily_loss": 1000,   # ₹
    "max_trades_per_day": 50
}

LOG_FILE = "paper_trades.jsonl"


def load_trades():
    if not os.path.exists(LOG_FILE):
        return []

    trades = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                trades.append(json.loads(line))
            except:
                continue
    return trades


def calculate_total_pnl():
    trades = load_trades()

    total_cost = 0
    total_value = 0

    for t in trades:
        qty = t.get("qty", 0)
        entry = t.get("price", 0)
        live = t.get("live_price", entry)

        total_cost += qty * entry
        total_value += qty * live

    return total_value - total_cost


def check_risk(signal):
    trades = load_trades()

    # 1️⃣ Quantity check
    if signal["qty"] > RISK_CONFIG["max_trade_qty"]:
        return False, "Qty exceeds limit"

    # 2️⃣ Trade count
    if len(trades) > RISK_CONFIG["max_trades_per_day"]:
        return False, "Too many trades today"

    return True, "OK"