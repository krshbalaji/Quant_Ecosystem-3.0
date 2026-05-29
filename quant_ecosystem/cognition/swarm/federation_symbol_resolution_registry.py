from typing import List

from .symbol_collision import (
    SymbolCollision,
)


class FederationSymbolResolutionRegistry:

    def __init__(self):
        self._collisions: List[
            SymbolCollision
        ] = []

    def register(
        self,
        collision: SymbolCollision,
    ) -> None:

        self._collisions.append(
            collision
        )

    def collisions(self):

        return list(
            self._collisions
        )

    def count(self) -> int:

        return len(
            self._collisions
        )