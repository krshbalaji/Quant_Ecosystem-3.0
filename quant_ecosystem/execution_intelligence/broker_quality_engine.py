class BrokerQualityEngine:

    def score(
        self,
        fill_rate,
        avg_latency_ms,
        rejection_rate,
    ):
        score = fill_rate

        score -= avg_latency_ms / 100.0
        score -= rejection_rate * 100.0

        if score < 0:
            score = 0

        return round(score, 2)

    def rank(
        self,
        broker_metrics,
    ):
        ranked = []

        for broker, metrics in broker_metrics.items():
            ranked.append(
                {
                    "broker": broker,
                    "score": self.score(
                        metrics["fill_rate"],
                        metrics["avg_latency_ms"],
                        metrics["rejection_rate"],
                    ),
                }
            )

        return sorted(
            ranked,
            key=lambda x: x["score"],
            reverse=True,
        )


broker_quality_engine = (
    BrokerQualityEngine()
)