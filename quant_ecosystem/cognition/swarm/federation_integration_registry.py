from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .integration_contract import (
    IntegrationContract,
)


class FederationIntegrationRegistry(
    KeyedRegistry[
        str,
        IntegrationContract
    ]
):

    def register(
        self,
        contract: IntegrationContract,
    ) -> None:

        super().register(
            contract.target_system,
            contract,
        )

    def enabled(
        self,
        target_system: str,
    ) -> bool:

        contract = self.get(
            target_system
        )

        return (
            contract is not None
            and contract.enabled
        )