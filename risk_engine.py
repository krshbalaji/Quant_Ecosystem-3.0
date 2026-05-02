import json
import os

RISK_CONFIG = {
    "max_trade_qty": 5,
    "max_daily_loss": 1000,
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


def check_risk(signal):
    trades = load_trades()

    symbol = signal.get("symbol")
    qty = int(signal.get("qty", 0))

    # ✅ 1. Quantity limit
    if qty > RISK_CONFIG["max_trade_qty"]:
        return False, "Qty exceeds limit"

    # ✅ 2. Trade count
    if len(trades) > RISK_CONFIG["max_trades_per_day"]:
        return False, "Too many trades today"

    return True, "OK"