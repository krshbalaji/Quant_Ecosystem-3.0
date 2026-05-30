from quant_ecosystem.cognition.swarm import (
    PerformanceSnapshot,
)


def test_performance_snapshot():

    snapshot = PerformanceSnapshot(
        execution_id="E1",
        successful=True,
    )

    assert snapshot.successful