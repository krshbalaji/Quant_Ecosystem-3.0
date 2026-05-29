from quant_ecosystem.cognition.swarm import (
    FederationReadinessRegistry,
    ReadinessStatus,
)


def test_readiness_registry():

    registry = (
        FederationReadinessRegistry()
    )

    registry.register(
        ReadinessStatus(
            capability_id="governance",
            ready=True,
        )
    )

    assert registry.count() == 1
    assert registry.ready_count() == 1