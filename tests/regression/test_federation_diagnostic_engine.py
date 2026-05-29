from quant_ecosystem.cognition.swarm import (
    FederationCapability,
    FederationCapabilityRegistry,
    FederationDiagnosticEngine,
)


def test_diagnostic_engine():

    registry = (
        FederationCapabilityRegistry()
    )

    registry.register(
        FederationCapability(
            capability_id="governance",
            capability_type="core",
        )
    )

    report = (
        FederationDiagnosticEngine()
        .evaluate(registry)
    )

    assert report.total_capabilities == 1