class AnomalyDetector:

    def anomaly_score(
        self,
        *,
        broker_health,
        liquidity,
        volatility,
    ):

        score = 0.0

        if broker_health < 0.30:
            score += 0.40

        if liquidity < 0.20:
            score += 0.30

        if volatility > 0.90:
            score += 0.40

        return round(
            min(score, 1.0),
            4,
        )


anomaly_detector = (
    AnomalyDetector()
)