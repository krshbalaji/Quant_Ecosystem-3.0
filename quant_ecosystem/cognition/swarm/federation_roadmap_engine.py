from .federation_roadmap_registry import (
    FederationRoadmapRegistry,
)
from .roadmap_step import (
    RoadmapStep,
)
from .strategic_roadmap import (
    StrategicRoadmap,
)


class FederationRoadmapEngine:

    def generate(
        self,
        registry: FederationRoadmapRegistry,
    ) -> StrategicRoadmap:

        steps = []

        for order, objective in enumerate(
            registry.objectives(),
            start=1,
        ):
            steps.append(
                RoadmapStep(
                    objective_id=(
                        objective.objective_id
                    ),
                    execution_order=order,
                )
            )

        return StrategicRoadmap(
            roadmap_steps=steps
        )