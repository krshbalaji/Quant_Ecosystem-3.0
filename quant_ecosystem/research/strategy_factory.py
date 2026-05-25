from quant_ecosystem.strategy_execution import (
    StrategyExecutionIntent,
    StrategyRiskBudget,
)


class StrategyFactory:

    def create_intent(
        self,
        opportunity,
        broker="fyers",
        qty=1,
    ):
        direction = (
            "BUY"
            if opportunity.metadata.get(
                "direction"
            ) == "LONG"
            else "SELL"
        )

        return StrategyExecutionIntent(
            strategy_id=(
                f"alpha_{opportunity.symbol}"
            ),
            symbol=opportunity.symbol,
            side=direction,
            qty=qty,
            broker=broker,
            metadata={
                "alpha_score": (
                    opportunity.alpha_score
                ),
                "confidence": (
                    opportunity.confidence
                ),
                "rank": opportunity.rank,
            },
        )

    def create_risk_budget(
        self,
        opportunity,
        capital_limit=100000,
        max_loss=5000,
        max_position=100,
    ):
        return StrategyRiskBudget(
            strategy_id=(
                f"alpha_{opportunity.symbol}"
            ),
            max_capital=capital_limit,
            max_positions=max_position,
            max_loss=max_loss,
        )

    def batch_create(
        self,
        ranked_opportunities,
        broker="fyers",
        qty=1,
    ):
        intents = []

        for opportunity in ranked_opportunities:
            intents.append(
                self.create_intent(
                    opportunity,
                    broker=broker,
                    qty=qty,
                )
            )

        return intents


strategy_factory = StrategyFactory()