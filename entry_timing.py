import numpy as np

def confirm_entry(md, decision):
    """
    md: {price, high, low, atr}
    decision: {side, strength}
    """

    price = md["price"]
    high = md["high"]
    low = md["low"]
    atr = md.get("atr", 0.0)

    # ---- basic sanity ----
    if atr == 0:
        return False, "No ATR"

    # ---- breakout confirmation ----
    if decision["side"] == "BUY":
        breakout = price >= high * 0.999  # near high
        momentum = (high - low) > atr * 0.5
        if breakout and momentum:
            return True, "Breakout + momentum"

    if decision["side"] == "SELL":
        breakdown = price <= low * 1.001
        momentum = (high - low) > atr * 0.5
        if breakdown and momentum:
            return True, "Breakdown + momentum"

    return False, "No confirmation"