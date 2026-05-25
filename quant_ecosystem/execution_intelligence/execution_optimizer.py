from quant_ecosystem.execution_intelligence.broker_quality_engine import (
    broker_quality_engine,
)

from quant_ecosystem.execution_intelligence.slippage_intelligence import (
    slippage_intelligence,
)


class ExecutionOptimizer:

    def recommend_route(
        self,
        broker_metrics,
    ):
        ranked = (
            broker_quality_engine.rank(
                broker_metrics
            )
        )

        return ranked[0]

    def slippage_assessment(
        self,
        expected_price,
        actual_price,
    ):
        bps = (
            slippage_intelligence
            .estimate_bps(
                expected_price,
                actual_price,
            )
        )

        return {
            "bps": bps,
            "classification": (
                slippage_intelligence
                .classify(bps)
            ),
        }

    def optimize(
        self,
        broker_metrics,
        expected_price,
        actual_price,
    ):
        return {
            "route": self.recommend_route(
                broker_metrics
            ),
            "slippage": (
                self.slippage_assessment(
                    expected_price,
                    actual_price,
                )
            ),
        }


execution_optimizer = (
    ExecutionOptimizer()
)