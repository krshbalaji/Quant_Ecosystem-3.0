from typing import Dict

from .integration_contract import (
    IntegrationContract,
)


class FederationIntegrationRegistry:

    def __init__(self):
        self._contracts: Dict[
            str,
            IntegrationContract,
        ] = {}

    def register(
        self,
        contract: IntegrationContract,
    ) -> None:

        self._contracts[
            contract.target_system
        ] = contract

    def get(
        self,
        target_system: str,
    ):

        return self._contracts.get(
            target_system
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