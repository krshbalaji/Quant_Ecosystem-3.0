from quant_ecosystem.cognition.swarm import (
    FederationPerformanceRegistry,
    PerformanceSnapshot,
)


def test_performance_registry():

    registry = (
        FederationPerformanceRegistry()
    )

    registry.register(
        PerformanceSnapshot(
            execution_id="E1",
            successful=True,
        )
    )

    assert registry.count() == 1