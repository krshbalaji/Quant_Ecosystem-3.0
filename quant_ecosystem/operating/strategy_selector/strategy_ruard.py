import json

FILE = "trade_journal.json"


class StrategyGuard:

    def load(self):
        try:
            with open(FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def evaluate(self):

        data = self.load()

        performance = {}

        for t in data:
            s = t["strategy"]
            pnl = t["pnl"]

            performance[s] = performance.get(s, 0) + pnl

        disabled = []

        for s, pnl in performance.items():
            if pnl < -1000:  # threshold (adjust later)
                disabled.append(s)

        return disabled