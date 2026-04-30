import json
import os
import yfinance as yf

LOG_FILE = "paper_trades.jsonl"


def load_trades():
    if not os.path.exists(LOG_FILE):
        return []

    trades = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                trades.append(json.loads(line))
            except:
                continue
    return trades


def get_price(symbol):
    try:
        ticker = "^NSEI" if symbol == "NIFTY" else symbol
        return float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
    except:
        return 0.0


def calculate():
    trades = load_trades()

    portfolio = {}

    for t in trades:
        sym = t["symbol"]
        qty = t["qty"]
        price = t["price"]

        if sym not in portfolio:
            portfolio[sym] = {"qty": 0, "cost": 0}

        portfolio[sym]["qty"] += qty
        portfolio[sym]["cost"] += qty * price

    total_value = 0
    total_cost = 0

    print("\n--- PORTFOLIO ---")

    for sym, data in portfolio.items():
        live_price = get_price(sym)
        value = data["qty"] * live_price
        pnl = value - data["cost"]

        total_value += value
        total_cost += data["cost"]

        print(f"{sym} | Qty: {data['qty']} | Live: {round(live_price,2)} | Value: {round(value,2)} | PnL: {round(pnl,2)}")

    print("\nTotal Value:", round(total_value, 2))
    print("Total Cost:", round(total_cost, 2))
    print("Total PnL:", round(total_value - total_cost, 2))


if __name__ == "__main__":
    calculate()