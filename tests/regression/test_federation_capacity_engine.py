from quant_ecosystem.cognition.swarm import (
    CapacityMetric,
    FederationCapacityEngine,
    FederationCapacityRegistry,
)


def test_capacity_engine():

    registry = (
        FederationCapacityRegistry()
    )

    registry.register(
        CapacityMetric(
            category_name="execution",
            total_capacity=100.0,
            utilized_capacity=80.0,
        )
    )

    registry.register(
        CapacityMetric(
            category_name="decision",
            total_capacity=100.0,
            utilized_capacity=40.0,
        )
    )

    report = (
        FederationCapacityEngine()
        .evaluate(registry)
    )

    assert (
        report.highest_utilization_category
        == "execution"
    )

    assert (
        report.utilization_ratio
        == 0.8
    )