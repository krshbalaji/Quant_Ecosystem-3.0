from typing import List

from .capability_dependency import (
    CapabilityDependency,
)


class CapabilityDependencyRegistry:

    def __init__(self):
        self._dependencies: List[
            CapabilityDependency
        ] = []

    def register(
        self,
        dependency: CapabilityDependency,
    ) -> None:

        self._dependencies.append(
            dependency
        )

    def count(self) -> int:

        return len(
            self._dependencies
        )

    def dependencies(self):

        return list(
            self._dependencies
        )