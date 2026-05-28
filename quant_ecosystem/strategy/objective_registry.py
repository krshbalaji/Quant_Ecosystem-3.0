from quant_ecosystem.strategy.strategic_objective import (
    StrategicObjective,
)


class ObjectiveRegistry:

    def __init__(self):

        self._objective = (
            StrategicObjective(
                objective_name=(
                    "SOVEREIGN_SURVIVAL"
                ),
                priority=10,
                survival_weight=0.80,
                opportunity_weight=0.20,
            )
        )

    def current(self):

        return self._objective


objective_registry = (
    ObjectiveRegistry()
)