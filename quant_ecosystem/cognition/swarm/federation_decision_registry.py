from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .decision_candidate import (
    DecisionCandidate,
)


class FederationDecisionRegistry(
    AppendRegistry[
        DecisionCandidate
    ]
):

    def candidates(
        self,
    ) -> list[DecisionCandidate]:

        return self.entries()