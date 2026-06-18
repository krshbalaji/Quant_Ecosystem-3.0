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
        contract_or_key,
        value=None,
    ) -> None:

        if value is None:
            super().register(
                contract_or_key.adapter_id,
                contract_or_key,
            )
        else:
            super().register(
                contract_or_key,
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