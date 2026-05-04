import json
import os
from firestore_client import get_positions

RISK_CONFIG = {
    "max_trade_qty": 5,
    "max_daily_loss": 1000,
    "max_trades_per_day": 50,

    # 🔥 NEW (portfolio level)
    "max_total_positions": 5,
    "max_symbol_qty": 100,
    "max_capital_per_symbol": 100000
}

LOG_FILE = "paper_trades.jsonl"


# ---- LOAD TRADE HISTORY ----
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


# ---- EXISTING TRADE CHECK (UNCHANGED) ----
def check_risk(signal):
    trades = load_trades()

    qty = int(signal.get("qty", 0))

    # 🔥 ADAPTIVE LIMIT
    dynamic_limit = RISK_CONFIG["max_trade_qty"]

    if len(trades) > 20:
        dynamic_limit = int(dynamic_limit * 0.7)

    if len(trades) > 40:
        dynamic_limit = int(dynamic_limit * 0.5)

    if qty > dynamic_limit:
        print(f"[RISK ADJUST] Reducing qty {qty} → {dynamic_limit}")
        signal["qty"] = dynamic_limit

    if len(trades) > RISK_CONFIG["max_trades_per_day"]:
        return False, "Too many trades today"

    return True, "OK"

    print(f"[RISK STATE] {symbol} existing={existing_qty} incoming={qty} limit={limit}")

# ---- NEW: PORTFOLIO RISK ----
def check_portfolio_risk(symbol, qty, price, strength):
    positions = get_positions() or {}
    limit = RISK_CONFIG["max_symbol_qty"]

    existing_qty = positions.get(symbol, {}).get("qty", 0)

    print(f"[RISK STATE] {symbol} existing={existing_qty} incoming={qty} limit={limit}")

    # --- already above/at limit
    if existing_qty >= limit:
        if strength >= 1.2:
            print("[RISK REBALANCE] Allowing minimal scaling")
            return True, "rebalance", 1   # ✅ return adjusted qty
        else:
            return False, "Symbol already at max capacity", 0

    if existing_qty > limit:
        trim = int((existing_qty - limit) * 0.2)  # trim 20% of excess
        trim = max(1, trim)
        print(f"[RISK TRIM] Reducing {symbol} by {trim} to move toward limit")
        return True, "trim", -trim  # negative qty means reduce position
        
    # --- partial cap
    if existing_qty + qty > limit:
        allowed_qty = limit - existing_qty
        if allowed_qty <= 0:
            return False, "No capacity left", 0

        print(f"[RISK ADJUST] Scaling reduced {qty} → {allowed_qty}")
        return True, "adjusted", allowed_qty

    return True, "OK", qty


# ---- MASTER CHECK (NEW ENTRY POINT) ----
def allow_trade(signal, price):
    symbol = signal["symbol"]
    qty = int(signal.get("qty", 0))
    strength = signal.get("strength", 0)

    ok, msg, new_qty = check_portfolio_risk(symbol, qty, price, strength)
    
    signal["qty"] = new_qty  # can be positive (add) or negative (trim)

    if not ok:
        print(f"[RISK BLOCKED] {msg}")
        return False

    # ✅ write back adjusted qty
    signal["qty"] = max(1, int(new_qty))

    return True