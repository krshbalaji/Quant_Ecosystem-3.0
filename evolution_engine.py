import json

FILE = "trade_journal.json"

def strategy_scores():

    try:
        with open(FILE, "r") as f:
            data = json.load(f)
    except:
        return {}

    scores = {}

    for t in data:
        s = t["strategy"]
        scores[s] = scores.get(s, 0) + t["pnl"]

    return scores


def best_strategy(regime=None):

    scores = strategy_scores()

    if not scores:
        return None

    return max(scores, key=scores.get)


def worst_strategy():

    scores = strategy_scores()

    if not scores:
        return None

    return min(scores, key=scores.get)