from typing import List

from .architecture_component import (
    ArchitectureComponent,
)


class FederationArchitectureInventoryRegistry:

    def __init__(self):
        self._components: List[
            ArchitectureComponent
        ] = []

    def register(
        self,
        component: ArchitectureComponent,
    ) -> None:

        self._components.append(
            component
        )

    def components(self):

        return list(
            self._components
        )

    def count(self) -> int:

        return len(
            self._components
        )