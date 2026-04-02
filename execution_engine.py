from broker_fyers import place_order

def execute_trade(strategy, capital, symbol):

    if capital == 0:
        print("❌ No trade")
        return

    # Simple logic (you can enhance later)
    if strategy == "EMA_PULLBACK":
        side = "BUY"
    elif strategy == "ORB_SCALP":
        side = "BUY"
    else:
        return
    if qty == 0:
        print("❌ Position size too small — skip trade")
        return

    from trade_manager import calculate_target, manage_trade
    import time

    entry = entry   # already calculated
    target = calculate_target(entry, sl)

    print(f"🎯 Target: {target}")

    # -------- LIVE MONITOR LOOP -------- #

    while True:

        result = manage_trade(symbol, entry, sl, target)

        if isinstance(result, tuple):
            sl = result[1]  # updated SL

        if status == "EXIT":
            print("🚪 Closing trade...")
            break

        time.sleep(60)  # check every 1 min    

    from risk_engine import position_size, calculate_sl
    import yfinance as yf

    df = yf.download(symbol, period="1d", interval="5m", progress=False)

    entry = df["Close"].iloc[-1]
    sl = calculate_sl(df)

    qty = position_size(entry, sl)

    print(f"Entry: {entry}")
    print(f"SL: {sl}")
    print(f"Qty: {qty}")

    print(f"🚀 Executing {side} {symbol}")

    response = place_order(symbol, qty, side)

    print("Broker Response:", response)