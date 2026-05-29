from quant_ecosystem.cognition.swarm import (
    FederationCapability,
    FederationCapabilityEngine,
    FederationCapabilityRegistry,
)


def test_capability_inventory():

    registry = (
        FederationCapabilityRegistry()
    )

    registry.register(
        FederationCapability(
            capability_id="allocation",
            capability_type="governance",
        )
    )

    inventory = (
        FederationCapabilityEngine()
        .inventory(registry)
    )

    assert inventory.total_capabilities == 1
    assert inventory.active_capabilities == 1