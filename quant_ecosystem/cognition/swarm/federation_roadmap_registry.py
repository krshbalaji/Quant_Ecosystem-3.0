from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .prioritized_objective import (
    PrioritizedObjective,
)


class FederationRoadmapRegistry(
    AppendRegistry[
        PrioritizedObjective
    ]
):

    def objectives(
        self,
    ) -> list[
        PrioritizedObjective
    ]:

        return sorted(
            self.entries(),
            key=lambda x: (
                x.priority_rank
            ),
        )