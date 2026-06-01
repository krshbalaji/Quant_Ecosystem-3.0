from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .strategic_objective import (
    StrategicObjective,
)


class FederationPrioritizationRegistry(
    AppendRegistry[
        StrategicObjective
    ]
):

    def objectives(
        self,
    ) -> list[
        StrategicObjective
    ]:

        return self.entries()