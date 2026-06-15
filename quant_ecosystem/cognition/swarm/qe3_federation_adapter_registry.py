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
        key: str,
        value: GovernanceAdapterContract,
    ) -> None:
        super().register(key, value)

    def get(
        self,
        key: str,
    ) -> GovernanceAdapterContract | None:
        return super().get(key)

    def register_contract(
        self,
        contract: GovernanceAdapterContract,
    ) -> None:

        self.register(
            contract.subsystem_name,
            contract,
        )

    def get_contract(
        self,
        subsystem_name: str,
    ) -> GovernanceAdapterContract | None:

        try:
            return super().get(subsystem_name)
        except Exception:
            return None

    def enabled(
        self,
        subsystem_name: str,
    ) -> bool:

        contract = self.get_contract(
            subsystem_name
        )

        return (
            contract is not None
            and contract.enabled
        )