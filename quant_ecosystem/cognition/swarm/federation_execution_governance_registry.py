from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .execution_initiative import (
    ExecutionInitiative,
)


class FederationExecutionGovernanceRegistry(
    AppendRegistry[
        ExecutionInitiative
    ]
):

    def initiatives(
        self,
    ) -> list[
        ExecutionInitiative
    ]:

        return self.entries()