from quant_ecosystem.cognition.swarm import (
    ArchitectureComponent,
    FederationArchitectureInventoryEngine,
    FederationArchitectureInventoryRegistry,
)


def test_inventory_engine():

    registry = (
        FederationArchitectureInventoryRegistry()
    )

    registry.register(
        ArchitectureComponent(
            component_name="EngineA",
            component_type="engine",
        )
    )

    report = (
        FederationArchitectureInventoryEngine()
        .evaluate(
            registry
        )
    )

    assert report.total_components == 1