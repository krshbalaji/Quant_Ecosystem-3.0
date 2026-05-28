from quant_ecosystem.learning.learning_memory import (
    learning_memory,
)


class LearningEngine:

    def learn(
        self,
        *,
        broker,
        latency_ms,
        retry_count,
        success,
    ):

        learning_memory.record(
            {
                "broker": broker,
                "latency_ms": latency_ms,
                "retry_count": retry_count,
                "success": success,
            }
        )

    def broker_score(
        self,
        broker,
    ):

        relevant = []

        for event in (
            learning_memory.events()
        ):

            if (
                event.get(
                    "broker"
                )
                == broker
            ):
                relevant.append(
                    event
                )

        if not relevant:
            return 1.0

        success_rate = (
            sum(
                1
                for x in relevant
                if x.get("success")
            )
            / len(relevant)
        )

        avg_latency = (
            sum(
                x.get(
                    "latency_ms",
                    0.0,
                )
                for x in relevant
            )
            / len(relevant)
        )

        latency_penalty = min(
            0.5,
            avg_latency / 10000.0,
        )

        return max(
            0.1,
            success_rate
            - latency_penalty,
        )


learning_engine = (
    LearningEngine()
)