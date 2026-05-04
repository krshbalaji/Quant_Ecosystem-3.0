from datetime import datetime, timedelta
from market_data_provider import provider
from broker.paper_broker import broker
from ai_memory import record_trade

TRAIL_PCT = 0.01
STOP_LOSS_PCT = 0.02
MAX_HOLD_MIN = 15

positions = {}

def calculate_pnl(entry, current, side, qty):
    return (current - entry) * qty if side == "BUY" else (entry - current) * qty


def register_position(symbol, side, qty, price):
    positions[symbol] = {
        "side": side,
        "qty": qty,
        "entry_price": price,
        "highest": price,
        "lowest": price,
        "entry_time": datetime.now()
    }
    print(f"[EXIT ENGINE] Registered position: {symbol}")


def check_exits(market_data=None):

    to_remove = []

    for symbol, pos in list(positions.items()):

        try:
            md = market_data.get(symbol) if market_data else provider.get_data(symbol)
            if not md:
                continue

            price = md["price"]
            side = pos["side"]

            # update extremes
            if side == "BUY":
                pos["highest"] = max(pos["highest"], price)
                if price < pos["highest"] * (1 - TRAIL_PCT):
                    exit_trade(symbol, pos, price, "TRAIL")
                    to_remove.append(symbol)
                    continue
                if price < pos["entry_price"] * (1 - STOP_LOSS_PCT):
                    exit_trade(symbol, pos, price, "SL")
                    to_remove.append(symbol)
                    continue
            else:
                pos["lowest"] = min(pos["lowest"], price)
                if price > pos["lowest"] * (1 + TRAIL_PCT):
                    exit_trade(symbol, pos, price, "TRAIL")
                    to_remove.append(symbol)
                    continue
                if price > pos["entry_price"] * (1 + STOP_LOSS_PCT):
                    exit_trade(symbol, pos, price, "SL")
                    to_remove.append(symbol)
                    continue

            if datetime.now() - pos["entry_time"] > timedelta(minutes=MAX_HOLD_MIN):
                exit_trade(symbol, pos, price, "TIME")
                to_remove.append(symbol)

        except Exception as e:
            print(f"[EXIT ERROR] {symbol}: {e}")

    for s in to_remove:
        positions.pop(s, None)

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