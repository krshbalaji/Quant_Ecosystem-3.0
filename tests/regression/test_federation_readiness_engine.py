from quant_ecosystem.cognition.swarm import (
    FederationReadinessEngine,
    FederationReadinessRegistry,
    ReadinessStatus,
)


def test_readiness_engine():

    registry = (
        FederationReadinessRegistry()
    )

    registry.register(
        ReadinessStatus(
            capability_id="audit",
            ready=True,
        )
    )

    report = (
        FederationReadinessEngine()
        .evaluate(registry)
    )

    assert report.operationally_ready