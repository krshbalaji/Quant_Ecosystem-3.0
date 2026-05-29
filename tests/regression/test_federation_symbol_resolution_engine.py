from quant_ecosystem.cognition.swarm import (
    FederationSymbolResolutionEngine,
    FederationSymbolResolutionRegistry,
    SymbolCollision,
)


def test_resolution_engine():

    registry = (
        FederationSymbolResolutionRegistry()
    )

    registry.register(
        SymbolCollision(
            symbol_name="ExecutionInitiative",
            primary_module="module_a",
            conflicting_module="module_b",
        )
    )

    resolutions, report = (
        FederationSymbolResolutionEngine()
        .resolve(
            registry
        )
    )

    assert len(resolutions) == 1
    assert report.collision_count == 1