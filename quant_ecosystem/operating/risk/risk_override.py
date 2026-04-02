import json

FILE = "trade_journal.json"


class RiskOverride:

    def load(self):
        try:
            with open(FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def check(self):

        data = self.load()

        if len(data) < 5:
            return False

        last = data[-5:]

        pnl = sum(t["pnl"] for t in last)

        if pnl < -2000:
            return True

        return False