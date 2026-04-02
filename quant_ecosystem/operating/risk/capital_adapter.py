import json

FILE = "trade_journal.json"


class CapitalAdapter:

    def load(self):
        try:
            with open(FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def get_multiplier(self):

        data = self.load()

        if len(data) < 5:
            return 1.0

        last_trades = data[-5:]

        pnl = sum(t["pnl"] for t in last_trades)

        if pnl > 0:
            return 1.5  # scale up
        elif pnl < 0:
            return 0.5  # reduce risk
        else:
            return 1.0