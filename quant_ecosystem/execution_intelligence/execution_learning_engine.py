from quant_ecosystem.execution_intelligence.broker_memory import (
    broker_memory,
)


class ExecutionLearningEngine:

    def trust_score(
        self,
        broker,
    ):
        snapshot = (
            broker_memory
            .broker_snapshot(
                broker
            )
        )

        score = (
            snapshot["success_rate"]
            * 100
        )

        score -= (
            snapshot["avg_slippage"]
            / 10
        )

        if score < 0:
            score = 0

        return round(score, 2)

    def adaptive_rank(
        self,
        brokers,
    ):
        ranked = []

        for broker in brokers:
            ranked.append(
                {
                    "broker": broker,
                    "trust_score": (
                        self.trust_score(
                            broker
                        )
                    ),
                }
            )

        return sorted(
            ranked,
            key=lambda x: x[
                "trust_score"
            ],
            reverse=True,
        )


execution_learning_engine = (
    ExecutionLearningEngine()
)