from quant_ecosystem.core.registry_threading import (
    ThreadSafeRegistry,
)

from .federation_capability import (
    FederationCapability,
)


class FederationCapabilityRegistry(
    ThreadSafeRegistry[
        str,
        FederationCapability,
    ]
):
    
    

    def register(
        self,
        key: str | FederationCapability,
        value: FederationCapability | None = None,
    ) -> None:

        from typing import cast
        
        if value is None:
            capability = cast(FederationCapability, key)

            super().register(
                capability.capability_id,
                capability,
            )
        else:
            super().register(
                cast(str, key),
                value,
            )
            
    def register_capability(
        self,
        capability: FederationCapability,
    ) -> None:

        if self.exists(
            capability.capability_id
        ):
            return

        super().register(
            capability.capability_id,
            capability,
        )

    def capabilities(
        self,
    ):

        return list(
            self.snapshot().values()
        )

    def active_count(
        self,
    ) -> int:

        return sum(
            1
            for capability
            in self.capabilities()
            if capability.active
        )