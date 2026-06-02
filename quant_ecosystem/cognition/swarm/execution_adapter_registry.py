from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .router_adapter_contract import (
    RouterAdapterContract,
)


class ExecutionAdapterRegistry(
    KeyedRegistry[
        str,
        RouterAdapterContract,
    ]
):

    def register(
        self,
        contract: RouterAdapterContract,
    ) -> None:

        super().register(
            contract.adapter_id,
            contract,
        )

    def get(
        self,
        adapter_id: str,
    ):
        return super().get(
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