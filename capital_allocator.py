# capital_allocator.py

import math
from config import Config

# ===== STATE =====
daily_risk_used = 0.0
open_positions = 0


def set_capital(capital):
    Config.ACCOUNT_CAPITAL = max(capital, 10000)


def _risk_amount():
    return Config.ACCOUNT_CAPITAL * Config.RISK_PER_TRADE_PCT


def _max_daily_risk():
    return Config.ACCOUNT_CAPITAL * Config.MAX_DAILY_RISK_PCT


def can_take_trade():
    global daily_risk_used, open_positions

    if open_positions >= Config.MAX_CONCURRENT:
        return False, "Max concurrent positions reached"

    if daily_risk_used >= _max_daily_risk():
        return False, "Daily risk limit reached"

    return True, "OK"


def compute_qty(price, sl, lot_size=1, max_lot_cap=None):

    risk_amt = _risk_amount()
    sl_distance = abs(price - sl)

    if sl_distance <= 0:
        return 0, "Invalid SL distance"

    qty = risk_amt / sl_distance
    qty = math.floor(qty / lot_size) * lot_size

    if qty <= 0:
        return 0, "Qty too small"

    if max_lot_cap:
        qty = min(qty, max_lot_cap * lot_size)

    return int(qty), "OK"


def register_trade(price, sl, qty):
    global daily_risk_used, open_positions

    risk_per_unit = abs(price - sl)
    total_risk = risk_per_unit * qty

    daily_risk_used += total_risk
    open_positions += 1


def close_position():
    global open_positions
    open_positions = max(0, open_positions - 1)


def reset_day(new_capital=None):
    global daily_risk_used, open_positions

    daily_risk_used = 0.0
    open_positions = 0

    if new_capital:
        set_capital(new_capital)