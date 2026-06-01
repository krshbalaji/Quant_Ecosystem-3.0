from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .improvement_candidate import (
    ImprovementCandidate,
)


class FederationImprovementRegistry(
    AppendRegistry[
        ImprovementCandidate
    ]
):

    def candidates(
        self,
    ) -> list[ImprovementCandidate]:

        return self.entries()