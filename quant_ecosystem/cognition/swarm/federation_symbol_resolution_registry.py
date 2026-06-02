from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .symbol_collision import (
    SymbolCollision,
)


class FederationSymbolResolutionRegistry(
    AppendRegistry[
        SymbolCollision
    ]
):

    def collisions(
        self,
    ) -> list[
        SymbolCollision
    ]:

        return self.entries()