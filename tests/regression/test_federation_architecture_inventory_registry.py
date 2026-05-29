from quant_ecosystem.cognition.swarm import (
    ArchitectureComponent,
    FederationArchitectureInventoryRegistry,
)


def test_inventory_registry():

    registry = (
        FederationArchitectureInventoryRegistry()
    )

    registry.register(
        ArchitectureComponent(
            component_name="RegistryA",
            component_type="registry",
        )
    )

    assert registry.count() == 1