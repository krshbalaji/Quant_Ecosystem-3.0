from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .architecture_classification import (
    ArchitectureClassification,
)


class FederationArchitectureClassificationRegistry(
    AppendRegistry[
        ArchitectureClassification
    ]
):

    def classifications(
        self,
    ) -> list[
        ArchitectureClassification
    ]:

        return self.entries()