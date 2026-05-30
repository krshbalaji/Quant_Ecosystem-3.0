from quant_ecosystem.cognition.swarm import (
    CapacityMetric,
)


def test_capacity_metric():

    metric = CapacityMetric(
        category_name="execution",
        total_capacity=100.0,
        utilized_capacity=50.0,
    )

    assert metric.total_capacity == 100.0
    assert metric.utilized_capacity == 50.0