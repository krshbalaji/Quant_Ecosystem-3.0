import time
from telegram_control import get_command
from telegram_notifier import send_telegram
from infra.execution_router import route_execution
from infra.broker import broker

# ===== CONTROL =====
WAIT_SECONDS = 15
MAX_TRADES = 4
LOSS_LIMIT = 2
COOLDOWN_AFTER_LOSS = 1800  # 30 min

# ===== STATE =====
trade_count = 0
loss_streak = 0
last_trade_time = 0


# precision_executor.py

# precision_executor.py

def execute_signal(symbol, side, qty, price, order_type="LIMIT"):
    """
    Stable, dependency-free execution (paper mode).
    Replace later with real broker adapter.
    """
    print(f"[ORDER] {order_type} {side} {qty} {symbol} @ {price}")
    print(f"[BROKER PAPER] {side} {qty} {symbol} @ {price}")
    return True

    
    global trade_count, loss_streak, last_trade_time

    if trade_count >= MAX_TRADES:
        print("[LIMIT] Max trades reached")
        return

    if loss_streak >= LOSS_LIMIT:
        print("[RISK] Loss streak hit → cooling down")
        time.sleep(COOLDOWN_AFTER_LOSS)
        loss_streak = 0
        return

    # ---- ALERT ----
    msg = f"""
🚨 SCALPING SIGNAL

{alloc['symbol']} {alloc['side']}
Price: {round(price,2)}

Reply:
/ok = manual
/skip = ignore
(auto if no reply)
"""
    send_telegram(msg)

    # ---- WAIT FOR USER ----
    start = time.time()
    action = None

    while time.time() - start < WAIT_SECONDS:
        ask_trade_details()

        if cmd in ["/ok", "/skip"]:
            action = cmd
            break

        time.sleep(1)

    # ---- USER ACTION ----
    if action == "/skip":
        print("[USER] Skipped")
        return

    if action == "/ok":
        print("[USER] Manual execution")
        trade_count += 1
        last_trade_time = time.time()
        return

    # ---- AUTO FALLBACK ----
    print("[AUTO] Executing trade")

    payload = {
        "symbol": alloc["symbol"],
        "side": alloc["side"],
        "qty": alloc["qty"],
        "price": price
    }

    try:
        res = route_execution(payload)

        if res.get("success"):
            print("[AUTO] Success")
            pnl = res.get("pnl", 0)

            if pnl < 0:
                loss_streak += 1
            else:
                loss_streak = 0

        else:
            print("[AUTO] Failed")

    except Exception as e:
        print(f"[AUTO ERROR] {e}")

    trade_count += 1
    last_trade_time = time.time()