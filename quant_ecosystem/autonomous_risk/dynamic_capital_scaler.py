from quant_ecosystem.autonomous_risk.live_risk_forecaster import (
    live_risk_forecaster,
)

from quant_ecosystem.autonomous_risk.regime_risk_adapter import (
    regime_risk_adapter,
)


class DynamicCapitalScaler:

    def scale(
        self,
        exposure,
        drawdown,
        pnl,
        regime,
        base_capital,
    ):
        score = (
            live_risk_forecaster
            .portfolio_risk_score(
                exposure,
                drawdown,
                pnl,
            )
        )

        health = (
            live_risk_forecaster
            .classify(score)
        )

        risk_factor = (
            regime_risk_adapter
            .adjust(regime)
        )

        multiplier = 1.0

        if health == "CRITICAL":
            multiplier = 0.25
        elif health == "HIGH":
            multiplier = 0.50
        elif health == "WATCH":
            multiplier = 0.75

        return {
            "risk_score": score,
            "health": health,
            "recommended_capital": round(
                base_capital
                * risk_factor
                * multiplier,
                2,
            ),
        }


dynamic_capital_scaler = (
    DynamicCapitalScaler()
)