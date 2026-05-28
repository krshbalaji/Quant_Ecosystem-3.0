class RealityValidator:

    def trustworthy(
        self,
        *,
        anomaly_score,
    ):

        return anomaly_score < 0.70


reality_validator = (
    RealityValidator()
)