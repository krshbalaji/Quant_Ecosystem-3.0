def compute_levels(md, side):
    """
    Returns: entry, stop_loss, target
    """

    price = md["price"]
    atr = md.get("atr", 0.0)

    if atr == 0:
        atr = price * 0.005  # fallback 0.5%

    # ---- scalping tuned ----
    SL_MULT = 0.8
    TP_MULT = 1.2

    if side == "BUY":
        sl = price - atr * SL_MULT
        tp = price + atr * TP_MULT
    else:
        sl = price + atr * SL_MULT
        tp = price - atr * TP_MULT

    return round(price, 2), round(sl, 2), round(tp, 2)