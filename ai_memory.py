import json
import os

FILE = "ai_memory.json"

def load_history():
    if not os.path.exists(FILE):
        return []
    with open(FILE, "r") as f:
        return json.load(f)

def save_history(history):
    with open(FILE, "w") as f:
        json.dump(history, f)

def record_trade(symbol, side, pnl):
    history = load_history()

    print(f"[AI MEMORY] Recording trade: {symbol} pnl={pnl}")

    history.append({
        "symbol": symbol,
        "side": side,
        "pnl": pnl
    })

    save_history(history)


def get_bias(symbol):
    history = load_history()

    relevant = [h for h in history if h["symbol"] == symbol]

    if len(relevant) < 1:
        return 0

    avg = sum(h["pnl"] for h in relevant) / len(relevant)

    return avg