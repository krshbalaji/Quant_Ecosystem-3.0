class MultiSymbolScorer:

    def score(self, results):

        if not results:
            return 0

        sharpes = [r.get("sharpe", 0) for r in results]

        stability = 1 / (1 + max(sharpes) - min(sharpes))

        avg = sum(sharpes) / len(sharpes)

        return avg * stability