import json

FILE = "trade_journal.json"


class AISelector:

    def load_data(self):
        try:
            with open(FILE, "r") as f:
                return json.load(f)
        except:
            return []

    def compute_metrics(self, data, strategy, regime):

        trades = [t for t in data if t["strategy"] == strategy]

        if not trades:
            return 0

        pnl = sum(t["pnl"] for t in trades)

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]

        win_rate = len(wins) / len(trades)

        drawdown = abs(sum(t["pnl"] for t in losses))

        regime_bonus = sum(
            t["pnl"] for t in trades if t["regime"] == regime
        )

        score = (
            pnl * 1.0 +
            win_rate * 100 +
            regime_bonus * 1.5 -
            drawdown * 0.5
        )

        return score

    def select(self, strategies, regime):

        data = self.load_data()

        best = None
        best_score = -999999

        for s in strategies:

            name = getattr(s, "name", None)

            score = self.compute_metrics(data, name, regime)

            if score > best_score:
                best = s
                best_score = score

        return best