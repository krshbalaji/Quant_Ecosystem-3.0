from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .governance_adapter_contract import (
    GovernanceAdapterContract,
)


class QE3FederationAdapterRegistry(
    KeyedRegistry[
        str,
        GovernanceAdapterContract,
    ]
):

    def register(
        self,
        contract: GovernanceAdapterContract,
    ) -> None:

        super().register(
            contract.subsystem_name,
            contract,
        )

    def get(
        self,
        subsystem_name: str,
    ):
        return super().get(
            subsystem_name
        )

    def enabled(
        self,
        subsystem_name: str,
    ) -> bool:

        contract = self.get(
            subsystem_name
        )

        return (
            contract is not None
            and contract.enabled
        )