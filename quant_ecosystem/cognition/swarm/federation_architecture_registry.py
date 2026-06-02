from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .federation_component import (
    FederationComponent,
)


class FederationArchitectureRegistry(
    KeyedRegistry[
        str,
        FederationComponent
    ]
):

    def register(
        self,
        component: FederationComponent,
    ) -> None:

        super().register(
            component.component_id,
            component,
        )