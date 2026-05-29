from quant_ecosystem.cognition.swarm import (
    FederationCapability,
    FederationCapabilityMonitor,
    FederationCapabilityRegistry,
)


def test_monitor():

    registry = (
        FederationCapabilityRegistry()
    )

    registry.register(
        FederationCapability(
            capability_id="audit",
            capability_type="core",
        )
    )

    results = (
        FederationCapabilityMonitor()
        .evaluate(registry)
    )

    assert len(results) == 1
    assert results[0].healthy