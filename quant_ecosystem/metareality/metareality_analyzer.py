from quant_ecosystem.metareality.cognition_confidence import (
    CognitionConfidence,
)


class MetaRealityAnalyzer:

    def analyze(
        self,
        *,
        survivability,
        anomaly_score,
        extinction_probability,
    ):

        confidence = max(
            0.0,
            1.0 - (
                (
                    anomaly_score
                    + extinction_probability
                ) / 2.0
            ),
        )

        uncertainty = (
            1.0 - confidence
        )

        blindspot_risk = (
            uncertainty
            * (1.0 - survivability)
        )

        return (
            CognitionConfidence(
                confidence_score=round(
                    confidence,
                    4,
                ),
                uncertainty_score=round(
                    uncertainty,
                    4,
                ),
                blindspot_risk=round(
                    blindspot_risk,
                    4,
                ),
            )
        )


metareality_analyzer = (
    MetaRealityAnalyzer()
)