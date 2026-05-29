from quant_ecosystem.cognition.swarm import (
    FederationSymbolResolutionRegistry,
    SymbolCollision,
)


def test_resolution_registry():

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

    assert registry.count() == 1