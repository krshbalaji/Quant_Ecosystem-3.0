from quant_ecosystem.cognition.swarm import (
    FederationCapability,
    FederationCapabilityRegistry,
)


def test_capability_registry():

    registry = (
        FederationCapabilityRegistry()
    )

    registry.register(
        FederationCapability(
            capability_id="governance",
            capability_type="cognition",
        )
    )

    assert registry.count() == 1