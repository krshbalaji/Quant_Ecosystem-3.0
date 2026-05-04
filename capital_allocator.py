# capital_allocator.py

import math

# ===== USER CONFIG =====
ACCOUNT_CAPITAL = 100000  # default fallback

def set_capital(capital):
    global ACCOUNT_CAPITAL
    ACCOUNT_CAPITAL = max(capital, 10000)  # minimum protection
            # update daily/weekly
def get_risk_pct():
    if ACCOUNT_CAPITAL < 50000:
        return 0.005   # 0.5%
    elif ACCOUNT_CAPITAL < 100000:
        return 0.0075
    return 0.01
def _risk_amount():
    return ACCOUNT_CAPITAL * get_risk_pct()
        
MAX_DAILY_RISK_PCT = 0.03       # 3%
MAX_TRADES_PER_DAY = 5
MAX_CONCURRENT = 1              # keep 1 for now (scalping)

# ===== STATE =====
daily_risk_used = 0.0
open_positions = 0


def _risk_amount():
    return ACCOUNT_CAPITAL * RISK_PER_TRADE_PCT


def _max_daily_risk():
    return ACCOUNT_CAPITAL * MAX_DAILY_RISK_PCT


def can_take_trade():
    global daily_risk_used, open_positions

    if open_positions >= MAX_CONCURRENT:
        return False, "Max concurrent positions reached"

    if daily_risk_used >= _max_daily_risk():
        return False, "Daily risk limit reached"

    return True, "OK"


def compute_qty(price, sl, lot_size=1, max_lot_cap=None):
    """
    price: entry price
    sl: stop loss price
    lot_size: for equities use 1, for F&O use contract lot size
    max_lot_cap: optional hard cap (e.g., 3–4 lots)
    """

    risk_amt = _risk_amount()
    sl_distance = abs(price - sl)

    if sl_distance <= 0:
        return 0, "Invalid SL distance"

    # raw qty by risk
    qty = risk_amt / sl_distance

    # round down to lot multiple
    qty = math.floor(qty / lot_size) * lot_size

    if qty <= 0:
        return 0, "Qty too small for given SL"

    # optional cap (for your rule: max 3/4 lots)
    if max_lot_cap:
        qty = min(qty, max_lot_cap * lot_size)

    return int(qty), "OK"


def register_trade(sl, price, qty):
    """
    Update daily risk usage when a trade is taken.
    """
    global daily_risk_used, open_positions

    risk_per_unit = abs(price - sl)
    total_risk = risk_per_unit * qty

    daily_risk_used += total_risk
    open_positions += 1


def close_position():
    global open_positions
    open_positions = max(0, open_positions - 1)


def reset_day(new_capital=None):
    global daily_risk_used, open_positions, ACCOUNT_CAPITAL

    daily_risk_used = 0.0
    open_positions = 0

    if new_capital:
        ACCOUNT_CAPITAL = new_capital