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

        if not breakout:
            # allow strong signals even without breakout
            if decision.get("strength", 0) > 0.8:
                return True, "strong override"
            return False, "no breakout"

        if not valid:
            if decision.get("strength", 0) > 1.3:
                return True, "strong override"
            return False, reason    
            
    if decision["side"] == "SELL":
        breakdown = price <= low * 1.001
        momentum = (high - low) > atr * 0.5
        if breakdown and momentum:
            return True, "Breakdown + momentum"

    return False, "No confirmation"