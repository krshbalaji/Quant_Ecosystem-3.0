from quant_ecosystem.research.strategy_factory import (
    strategy_factory,
)


class OpportunityDispatchEngine:

    def top_opportunities(
        self,
        ranked_opportunities,
        top_n=5,
    ):
        return ranked_opportunities[:top_n]

    def execution_candidates(
        self,
        ranked_opportunities,
        broker="fyers",
        qty=1,
    ):
        return (
            strategy_factory.batch_create(
                ranked_opportunities,
                broker=broker,
                qty=qty,
            )
        )

    def alert_payload(
        self,
        opportunity,
    ):
        return {
            "symbol": opportunity.symbol,
            "alpha_score": (
                opportunity.alpha_score
            ),
            "confidence": (
                opportunity.confidence
            ),
            "rank": opportunity.rank,
            "direction": (
                opportunity.metadata.get(
                    "direction"
                )
            ),
        }

    def dispatch(
        self,
        ranked_opportunities,
        top_n=5,
        broker="fyers",
        qty=1,
    ):
        selected = (
            self.top_opportunities(
                ranked_opportunities,
                top_n=top_n,
            )
        )

        candidates = (
            self.execution_candidates(
                selected,
                broker=broker,
                qty=qty,
            )
        )

        alerts = [
            self.alert_payload(x)
            for x in selected
        ]

        return {
            "selected": selected,
            "execution_candidates": candidates,
            "alerts": alerts,
        }


opportunity_dispatch_engine = (
    OpportunityDispatchEngine()
)