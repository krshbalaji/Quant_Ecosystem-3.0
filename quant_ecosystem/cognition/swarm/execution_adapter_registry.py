from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .router_adapter_contract import (
    RouterAdapterContract,
)


class RoueterAdapterRegistry(
    KeyedRegistry[
        str,
        RouterAdapterContract,
    ]
):

    def register(
        self,
        key: str,
        value: RouterAdapterContract,
    ) -> None:

        super().register(
            key,
            value,
        )

    def get(
        self,
        key: str,
    ) -> RouterAdapterContract | None:

        return super().get(
            key
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