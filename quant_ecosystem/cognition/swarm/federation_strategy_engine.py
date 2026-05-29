from .federation_strategy_registry import (
    FederationStrategyRegistry,
)
from .strategic_plan import (
    StrategicPlan,
)


class FederationStrategyEngine:

    def generate_plan(
        self,
        registry: FederationStrategyRegistry,
    ) -> StrategicPlan:

        objectives = (
            registry.objectives()
        )

        return StrategicPlan(
            objective_count=len(
                objectives
            ),
            objectives=objectives,
        )