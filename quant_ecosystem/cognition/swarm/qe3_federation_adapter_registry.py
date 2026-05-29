from typing import Dict

from .governance_adapter_contract import (
    GovernanceAdapterContract,
)


class QE3FederationAdapterRegistry:

    def __init__(self):
        self._contracts: Dict[
            str,
            GovernanceAdapterContract,
        ] = {}

    def register(
        self,
        contract: GovernanceAdapterContract,
    ) -> None:

        self._contracts[
            contract.subsystem_name
        ] = contract

    def get(
        self,
        subsystem_name: str,
    ):

        return self._contracts.get(
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