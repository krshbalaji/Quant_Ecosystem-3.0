from typing import List

from .architecture_classification import (
    ArchitectureClassification,
)


class FederationArchitectureClassificationRegistry:

    def __init__(self):
        self._items: List[
            ArchitectureClassification
        ] = []

    def register(
        self,
        item: ArchitectureClassification,
    ) -> None:

        self._items.append(item)

    def classifications(self):

        return list(self._items)

    def count(self) -> int:

        return len(self._items)