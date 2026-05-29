from .federation_symbol_resolution_registry import (
    FederationSymbolResolutionRegistry,
)
from .resolution_report import (
    ResolutionReport,
)
from .symbol_resolution import (
    SymbolResolution,
)


class FederationSymbolResolutionEngine:

    def resolve(
        self,
        registry: (
            FederationSymbolResolutionRegistry
        ),
    ):

        resolutions = []

        for collision in (
            registry.collisions()
        ):
            resolutions.append(
                SymbolResolution(
                    symbol_name=(
                        collision.symbol_name
                    ),
                    canonical_module=(
                        collision.primary_module
                    ),
                )
            )

        return (
            resolutions,
            ResolutionReport(
                collision_count=(
                    registry.count()
                ),
                resolution_count=len(
                    resolutions
                ),
            ),
        )