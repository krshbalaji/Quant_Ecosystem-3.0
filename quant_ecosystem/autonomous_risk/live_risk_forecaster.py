class LiveRiskForecaster:

    def portfolio_risk_score(
        self,
        exposure,
        drawdown,
        pnl,
    ):
        score = 0

        score += exposure / 100000

        if drawdown > 0:
            score += drawdown / 1000

        if pnl < 0:
            score += abs(pnl) / 2000

        return round(score, 2)

    def classify(
        self,
        score,
    ):
        if score >= 20:
            return "CRITICAL"

        if score >= 10:
            return "HIGH"

        if score >= 5:
            return "WATCH"

        return "NORMAL"


live_risk_forecaster = (
    LiveRiskForecaster()
)