import math

CONFIG = {
    "capital": 100000,        # total capital
    "risk_per_trade": 0.01,   # 1% risk
    "max_position_pct": 0.2,  # max 20% capital per trade
    "min_qty": 1
}


def calculate_qty(symbol, price, atr):
    if price <= 0 or atr <= 0:
        return 0

    capital = CONFIG["capital"]
    risk_amt = capital * CONFIG["risk_per_trade"]

    # risk per unit (ATR based SL)
    risk_per_unit = atr

    qty_risk = risk_amt / risk_per_unit

    # capital constraint
    max_capital_alloc = capital * CONFIG["max_position_pct"]
    qty_cap = max_capital_alloc / price

    qty = int(min(qty_risk, qty_cap))

    return max(CONFIG["min_qty"], qty)