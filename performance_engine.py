import json
import datetime

FILE = "trade_journal.json"

# -------- LOG TRADE -------- #

def log_trade(symbol, strategy, entry, exit_price, pnl, regime):

    trade = {
        "time": str(datetime.datetime.now()),
        "symbol": symbol,
        "strategy": strategy,
        "entry": entry,
        "exit": exit_price,
        "pnl": pnl,
        "regime": regime
    }

    try:
        with open(FILE, "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(trade)

    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

# -------- ANALYTICS -------- #

def analyze_performance():

    try:
        with open(FILE, "r") as f:
            data = json.load(f)
    except:
        print("No trades yet")
        return

    total = len(data)
    wins = [t for t in data if t["pnl"] > 0]
    losses = [t for t in data if t["pnl"] <= 0]

    win_rate = len(wins) / total * 100 if total > 0 else 0

    total_pnl = sum(t["pnl"] for t in data)

    print("\n📊 PERFORMANCE REPORT")
    print("Total Trades:", total)
    print("Win Rate:", round(win_rate,2), "%")
    print("Total PnL:", round(total_pnl,2))

    # -------- BEST STRATEGY -------- #

    strat_score = {}

    for t in data:
        s = t["strategy"]
        strat_score[s] = strat_score.get(s, 0) + t["pnl"]

    best = max(strat_score, key=strat_score.get)

    print("🔥 Best Strategy:", best)

    # -------- WORST REGIME -------- #

    regime_score = {}

    for t in data:
        r = t["regime"]
        regime_score[r] = regime_score.get(r, 0) + t["pnl"]

    worst = min(regime_score, key=regime_score.get)

    print("⚠️ Worst Regime:", worst)