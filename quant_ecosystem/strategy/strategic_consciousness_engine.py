from quant_ecosystem.strategy.objective_registry import (
    objective_registry,
)


class StrategicConsciousnessEngine:

    def strategic_bias(self):

        objective = (
            objective_registry
            .current()
        )

        return (
            objective.survival_weight,
            objective.opportunity_weight,
        )

    def mission(self):

        return (
            objective_registry
            .current()
            .objective_name
        )


strategic_consciousness_engine = (
    StrategicConsciousnessEngine()
)