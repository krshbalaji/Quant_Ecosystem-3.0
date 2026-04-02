import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
FILE = os.path.join(BASE_DIR, "trade_journal.json")

def log_trade(symbol, strategy, side, qty, pnl=0):

    trade = {
        "time": str(datetime.now()),
        "symbol": symbol,
        "strategy": strategy,
        "side": side,
        "qty": qty,
        "pnl": pnl
    }

    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump([], f)

    with open(FILE, "r") as f:
        data = json.load(f)

    data.append(trade)

    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)