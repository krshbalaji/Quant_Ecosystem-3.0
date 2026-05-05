from datetime import datetime, timedelta
from market_data_provider import provider
from broker.paper_broker import broker
from ai_memory import record_trade
# --- local position store ---
active_positions = {}

TRAIL_PCT = 0.01
STOP_LOSS_PCT = 0.02
MAX_HOLD_MIN = 15

positions = {}

def calculate_pnl(entry, current, side, qty):
    return (current - entry) * qty if side == "BUY" else (entry - current) * qty


def register_position(symbol, entry_price, qty):

    if isinstance(symbol, dict):
        symbol = symbol.get("symbol")

    active_positions[symbol] = {
        "entry_price": entry_price,
        "qty": qty,
        "max_price": entry_price
    }

    print(f"[EXIT ENGINE] Registered position: {symbol}")


def check_exits(symbol, current_price=None):

    if symbol not in active_positions:
        return None

    pos = active_positions[symbol]

    entry = pos["entry_price"]
    qty = pos["qty"]

    if current_price is None:
        return None

    pos["max_price"] = max(pos["max_price"], current_price)

    pnl_pct = (current_price - entry) / entry * 100

    # dynamic SL
    if pnl_pct < -1.2:
        return {"symbol": symbol, "side": "EXIT", "qty": qty, "reason": "SL"}

    # smart TP
    if pnl_pct > 1.5:
        return {"symbol": symbol, "side": "EXIT", "qty": qty, "reason": "TP"}

    # trailing
    drop = (pos["max_price"] - current_price) / pos["max_price"] * 100
    if drop > 0.6:
        return {"symbol": symbol, "side": "EXIT", "qty": qty, "reason": "TRAIL"}

    return None

    
def should_exit(pos, price):

    # ---- SL ----
    if pos["side"] == "BUY" and price <= pos["sl"]:
        return True, "SL"

    if pos["side"] == "SELL" and price >= pos["sl"]:
        return True, "SL"

    # ---- TP ----
    if pos["side"] == "BUY" and price >= pos["tp"]:
        return True, "TP"

    if pos["side"] == "SELL" and price <= pos["tp"]:
        return True, "TP"

    # ---- TRAILING ----
    if pos["side"] == "BUY" and price <= pos.get("trail", 0):
        return True, "TRAIL"

    if pos["side"] == "SELL" and price >= pos.get("trail", 999999):
        return True, "TRAIL"

    return False, None

def exit_trade(symbol, pos, price, reason):

    exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
    broker.place_order(symbol, exit_side, pos["qty"])

    pnl = calculate_pnl(pos["entry_price"], price, pos["side"], pos["qty"])

    print(f"[EXIT] {symbol} {reason} PnL={pnl}")

    record_trade(symbol, pos["side"], pnl)

    TRAIL_FACTOR = 0.5  # tighter for scalping

def update_trailing(pos, price):

    if pos["side"] == "BUY":
        new_trail = price - pos["atr"] * TRAIL_FACTOR
        pos["trail"] = max(pos.get("trail", pos["entry_price"]), new_trail)

    else:
        new_trail = price + pos["atr"] * TRAIL_FACTOR
        pos["trail"] = min(pos.get("trail", pos["entry_price"]), new_trail)

def trail_stop(current_price, entry, sl, side):
    profit = current_price - entry if side == "BUY" else entry - current_price

    if profit > 0:
        sl = max(sl, entry + profit * 0.5) if side == "BUY" else min(sl, entry - profit * 0.5)

    return sl
