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