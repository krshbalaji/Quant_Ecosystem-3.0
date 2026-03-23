class AlphaConfidenceEngine:

    def score(self, result):

        sharpe = result.get("sharpe", 0)
        pf = result.get("profit_factor", 1)
        trades = result.get("total_trades", 1)
        dd = result.get("max_dd", 0)

        robustness = min(1.0, trades / 80)

        confidence = (
            sharpe * 0.5
            + (pf - 1) * 0.7
            - dd * 0.01
        ) * robustness

        return confidence