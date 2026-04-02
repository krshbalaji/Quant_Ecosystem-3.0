import json

FILE = "trade_journal.json"


class LivePnLEngine:

    def load(self):
        try:
            with open(FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def summary(self):

        data = self.load()

        total = sum(t["pnl"] for t in data)

        wins = len([t for t in data if t["pnl"] > 0])
        losses = len([t for t in data if t["pnl"] <= 0])

        return {
            "total_pnl": total,
            "wins": wins,
            "losses": losses,
            "trades": len(data)
        }