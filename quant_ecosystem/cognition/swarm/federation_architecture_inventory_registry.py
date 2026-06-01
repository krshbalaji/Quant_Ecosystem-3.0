from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .architecture_component import (
    ArchitectureComponent,
)


class FederationArchitectureInventoryRegistry(
    AppendRegistry[
        ArchitectureComponent
    ]
):

    def components(
        self,
    ) -> list[
        ArchitectureComponent
    ]:

        return self.entries()