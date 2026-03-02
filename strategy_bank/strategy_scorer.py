class StrategyScorer:

    def score(self, report, correlation_penalty=0.0):
        sharpe = report.get("sharpe", 0.0)
        profit_factor = report.get("profit_factor", 0.0)
        expectancy = report.get("expectancy", 0.0)
        win_rate = report.get("win_rate", 0.0)
        drawdown = report.get("max_dd", 0.0)

        score = (
            (sharpe * 25.0)
            + (profit_factor * 20.0)
            + (expectancy * 20.0)
            + (win_rate * 10.0)
            - (drawdown * 15.0)
            - correlation_penalty
        )
        return round(score, 4)
