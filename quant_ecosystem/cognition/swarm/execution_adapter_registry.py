from typing import Dict

from .router_adapter_contract import (
    RouterAdapterContract,
)


class ExecutionAdapterRegistry:

    def __init__(self):
        self._contracts: Dict[
            str,
            RouterAdapterContract,
        ] = {}

    def register(
        self,
        contract: RouterAdapterContract,
    ) -> None:

        self._contracts[
            contract.adapter_id
        ] = contract

    def get(
        self,
        adapter_id: str,
    ):

        return self._contracts.get(
            adapter_id
        )

    def enabled(
        self,
        adapter_id: str,
    ) -> bool:

        contract = self.get(
            adapter_id
        )

        return (
            contract is not None
            and contract.enabled
        )