from .architecture_classification_report import (
    ArchitectureClassificationReport,
)
from .federation_architecture_classification_registry import (
    FederationArchitectureClassificationRegistry,
)


class FederationArchitectureClassifier:

    def evaluate(
        self,
        registry: (
            FederationArchitectureClassificationRegistry
        ),
    ) -> ArchitectureClassificationReport:

        categories = {
            item.category
            for item
            in registry.classifications()
        }

        return ArchitectureClassificationReport(
            total_components=(
                registry.count()
            ),
            total_categories=len(
                categories
            ),
        )