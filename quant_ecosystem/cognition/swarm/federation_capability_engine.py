from .capability_inventory import (
    CapabilityInventory,
)
from .federation_capability_registry import (
    FederationCapabilityRegistry,
)


class FederationCapabilityEngine:

    def inventory(
        self,
        registry: FederationCapabilityRegistry,
    ) -> CapabilityInventory:

        return CapabilityInventory(
            total_capabilities=(
                registry.count()
            ),
            active_capabilities=(
                registry.active_count()
            ),
        )