class CapitalIntelligenceEngine:

    def __init__(self, alpha_book):
        self.alpha_book = alpha_book

    # ---------------------------------------
    # DOMINANCE REBALANCE
    # ---------------------------------------

    def rebalance(self):

        alphas = list(self.alpha_book.live_alphas)

        if not alphas:
            return

        scored = []

        for g in alphas:

            pnl = getattr(g, "realized_pnl", 0.0)
            confidence = getattr(g, "alpha_confidence", 0.5)

            score = pnl * 0.6 + confidence * 0.4

            scored.append((g, score))

        # dominance ranking
        scored.sort(key=lambda x: x[1], reverse=True)

        total = 0.0
        weights = []

        for rank, (g, s) in enumerate(scored):

            dominance = max(0.01, (len(scored) - rank) ** 2)

            weights.append((g, dominance))
            total += dominance

        for g, w in weights:

            g.capital_weight = w / total