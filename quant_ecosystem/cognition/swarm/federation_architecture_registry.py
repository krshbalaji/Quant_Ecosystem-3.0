from typing import Dict

from .federation_component import (
    FederationComponent,
)


class FederationArchitectureRegistry:

    def __init__(self):
        self._components: Dict[
            str,
            FederationComponent,
        ] = {}

    def register(
        self,
        component: FederationComponent,
    ) -> None:

        self._components[
            component.component_id
        ] = component

    def count(self) -> int:

        return len(self._components)