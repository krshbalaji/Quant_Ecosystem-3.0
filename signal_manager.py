import time

# =========================================================
# SIGNAL MANAGER
# =========================================================

ACTIVE_SIGNALS = {}

SIGNAL_NEW = "NEW"
SIGNAL_PANEL = "PANEL_OPEN"
SIGNAL_WAITING = "WAITING_USER"
SIGNAL_CONFIRMED = "CONFIRMED"
SIGNAL_EXECUTING = "EXECUTING"
SIGNAL_EXECUTED = "EXECUTED"
SIGNAL_CANCELLED = "CANCELLED"
SIGNAL_FAILED = "FAILED"

DEFAULT_EXPIRY = 900  # 15 mins


# =========================================================
# CREATE SIGNAL
# =========================================================
def create_signal(
    symbol,
    side,
    entry,
    score=0,
    strength=0,
    regime="UNKNOWN"
):

    signal_id = f"{symbol}_{int(time.time())}"

    ACTIVE_SIGNALS[signal_id] = {
        "signal_id": signal_id,
        "symbol": symbol,
        "side": side,
        "entry": entry,
        "score": score,
        "strength": strength,
        "regime": regime,

        "qty": 1,
        "price": entry,

        "status": SIGNAL_NEW,

        "created_at": time.time(),
        "updated_at": time.time(),

        "executed": False,
        "cancelled": False,
        "failed": False,

        "telegram_message_id": None
    }

    return signal_id


# =========================================================
# GET SIGNAL
# =========================================================
def get_signal(signal_id):
    return ACTIVE_SIGNALS.get(signal_id)


# =========================================================
# UPDATE STATUS
# =========================================================
def update_signal_status(signal_id, status):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["status"] = status
    signal["updated_at"] = time.time()


# =========================================================
# UPDATE QTY
# =========================================================
def update_qty(signal_id, qty):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["qty"] = max(1, int(qty))
    signal["updated_at"] = time.time()


# =========================================================
# UPDATE PRICE
# =========================================================
def update_price(signal_id, price):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["price"] = price
    signal["updated_at"] = time.time()


# =========================================================
# ATTACH TELEGRAM MESSAGE
# =========================================================
def attach_message(signal_id, message_id):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["telegram_message_id"] = message_id


# =========================================================
# MARK EXECUTED
# =========================================================
def mark_executed(signal_id):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["executed"] = True
    signal["status"] = SIGNAL_EXECUTED
    signal["updated_at"] = time.time()


# =========================================================
# MARK CANCELLED
# =========================================================
def mark_cancelled(signal_id):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["cancelled"] = True
    signal["status"] = SIGNAL_CANCELLED
    signal["updated_at"] = time.time()


# =========================================================
# MARK FAILED
# =========================================================
def mark_failed(signal_id):

    signal = ACTIVE_SIGNALS.get(signal_id)

    if not signal:
        return

    signal["failed"] = True
    signal["status"] = SIGNAL_FAILED
    signal["updated_at"] = time.time()


# =========================================================
# CLEAN EXPIRED SIGNALS
# =========================================================
def cleanup_signals(expiry=DEFAULT_EXPIRY):

    now = time.time()

    expired = []

    for signal_id, signal in ACTIVE_SIGNALS.items():

        age = now - signal["updated_at"]

        if age > expiry:
            expired.append(signal_id)

    for signal_id in expired:
        ACTIVE_SIGNALS.pop(signal_id, None)


# =========================================================
# CHECK ACTIVE
# =========================================================
def has_active_signal(symbol):

    for signal in ACTIVE_SIGNALS.values():

        if signal["symbol"] != symbol:
            continue

        if signal["status"] in [
            SIGNAL_NEW,
            SIGNAL_PANEL,
            SIGNAL_WAITING,
            SIGNAL_CONFIRMED,
            SIGNAL_EXECUTING
        ]:
            return True

    return False


# =========================================================
# GET ACTIVE SIGNAL BY SYMBOL
# =========================================================
def get_active_signal(symbol):

    for signal_id, signal in ACTIVE_SIGNALS.items():

        if signal["symbol"] != symbol:
            continue

        if signal["status"] in [
            SIGNAL_NEW,
            SIGNAL_PANEL,
            SIGNAL_WAITING,
            SIGNAL_CONFIRMED,
            SIGNAL_EXECUTING
        ]:
            return signal_id, signal

    return None, None


# =========================================================
# DEBUG
# =========================================================
def print_signals():

    print("\n========== ACTIVE SIGNALS ==========")

    if not ACTIVE_SIGNALS:
        print("NO ACTIVE SIGNALS")
        return

    for signal_id, signal in ACTIVE_SIGNALS.items():

        print(
            f"{signal['symbol']} | "
            f"{signal['side']} | "
            f"{signal['status']} | "
            f"qty={signal['qty']} | "
            f"price={signal['price']}"
        )

    print("====================================\n")