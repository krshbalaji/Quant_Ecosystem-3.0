from .federation_prioritization_registry import (
    FederationPrioritizationRegistry,
)
from .prioritized_objective import (
    PrioritizedObjective,
)
from .prioritization_report import (
    PrioritizationReport,
)


class FederationPrioritizationEngine:

    def prioritize(
        self,
        registry: FederationPrioritizationRegistry,
    ) -> PrioritizationReport:

        ordered = sorted(
            registry.objectives(),
            key=lambda x: x.priority,
        )

        prioritized = []

        for rank, objective in enumerate(
            ordered,
            start=1,
        ):
            prioritized.append(
                PrioritizedObjective(
                    objective_id=(
                        objective.objective_id
                    ),
                    priority_rank=rank,
                    score=float(
                        max(
                            1,
                            100
                            - (
                                rank
                                - 1
                            )
                            * 10,
                        )
                    ),
                )
            )

        return PrioritizationReport(
            objective_count=len(
                prioritized
            ),
            objectives=prioritized,
        )