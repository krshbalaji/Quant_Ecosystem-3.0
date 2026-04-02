class PortfolioRegimeScorer:

    def score(self, alpha_book, regime_memory):

        mismatch = 0
        total = 0

        for g in alpha_book.live_alphas:

            trained = getattr(g, "trained_regime", None)

            current = regime_memory.get_current_regime(
                g.symbol,
                g.resolution,
            )

            total += 1

            if trained != current:
                mismatch += 1

        if total == 0:
            return 0.0

        return mismatch / total