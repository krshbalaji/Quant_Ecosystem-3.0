from quant_ecosystem.strategy.strategic_consciousness_engine import (
    strategic_consciousness_engine,
)


class StrategicAlignmentEngine:

    def aligned(
        self,
        *,
        survivability,
        stress_level,
    ):

        (
            survival_weight,
            opportunity_weight,
        ) = (
            strategic_consciousness_engine
            .strategic_bias()
        )

        score = (
            survivability
            * survival_weight
        ) - (
            stress_level
            * opportunity_weight
        )

        return score >= 0.10


strategic_alignment_engine = (
    StrategicAlignmentEngine()
)