from quant_ecosystem.learning.learning_engine import (
    learning_engine,
)


class AdaptiveBrokerSelector:

    def preferred(
        self,
        brokers,
    ):

        ranked = sorted(
            brokers,
            key=lambda x: (
                learning_engine
                .broker_score(x)
            ),
            reverse=True,
        )

        return ranked[0]


adaptive_broker_selector = (
    AdaptiveBrokerSelector()
)