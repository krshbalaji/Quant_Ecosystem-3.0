from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .federation_observation import (
    FederationObservation,
)


class CivilizationKnowledgeBase(
    AppendRegistry[
        FederationObservation
    ]
):

    def add(
        self,
        observation: FederationObservation,
    ) -> None:

        self.register(observation)

    def observations(
        self,
    ) -> list[FederationObservation]:

        return self.entries()