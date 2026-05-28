from quant_ecosystem.existential.existential_threat import (
    ExistentialThreat,
)


class ExistentialAnalyzer:

    def analyze(
        self,
        *,
        survivability,
        stress_level,
        anomaly_score,
    ):

        extinction_probability = min(
            1.0,
            (
                (1.0 - survivability)
                + stress_level
                + anomaly_score
            ) / 3.0,
        )

        systemic_fragility = (
            stress_level
            * (1.0 - survivability)
        )

        continuity_risk = (
            extinction_probability
            * systemic_fragility
        )

        return (
            ExistentialThreat(
                extinction_probability=round(
                    extinction_probability,
                    4,
                ),
                systemic_fragility=round(
                    systemic_fragility,
                    4,
                ),
                continuity_risk=round(
                    continuity_risk,
                    4,
                ),
            )
        )


existential_analyzer = (
    ExistentialAnalyzer()
)