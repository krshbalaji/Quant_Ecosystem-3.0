from .architecture_inventory_report import (
    ArchitectureInventoryReport,
)
from .federation_architecture_inventory_registry import (
    FederationArchitectureInventoryRegistry,
)


class FederationArchitectureInventoryEngine:

    def evaluate(
        self,
        registry: (
            FederationArchitectureInventoryRegistry
        ),
    ) -> ArchitectureInventoryReport:

        unique_types = {
            component.component_type
            for component
            in registry.components()
        }

        return ArchitectureInventoryReport(
            total_components=(
                registry.count()
            ),
            unique_types=len(
                unique_types
            ),
        )