from quant_ecosystem.cognition.swarm import (
    FederationPerformanceEngine,
    FederationPerformanceRegistry,
    PerformanceSnapshot,
)


def test_performance_engine():

    registry = (
        FederationPerformanceRegistry()
    )

    registry.register(
        PerformanceSnapshot(
            execution_id="E1",
            successful=True,
        )
    )

    registry.register(
        PerformanceSnapshot(
            execution_id="E2",
            successful=False,
        )
    )

    report = (
        FederationPerformanceEngine()
        .evaluate(
            registry
        )
    )

    assert report.total_executions == 2
    assert report.successful_executions == 1
    assert report.success_rate == 0.5