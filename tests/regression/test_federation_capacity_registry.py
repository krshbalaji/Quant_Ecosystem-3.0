from quant_ecosystem.cognition.swarm import (
    CapacityMetric,
    FederationCapacityRegistry,
)


def test_capacity_registry():

    registry = (
        FederationCapacityRegistry()
    )

    registry.register(
        CapacityMetric(
            category_name="execution",
            total_capacity=100.0,
            utilized_capacity=50.0,
        )
    )

    assert registry.count() == 1