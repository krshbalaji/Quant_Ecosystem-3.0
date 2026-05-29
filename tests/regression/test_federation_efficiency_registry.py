from quant_ecosystem.cognition.swarm import (
    ArchitectureEfficiencyMetric,
    FederationEfficiencyRegistry,
)


def test_efficiency_registry():

    registry = (
        FederationEfficiencyRegistry()
    )

    registry.register(
        ArchitectureEfficiencyMetric(
            category_name="governance",
            utilized_components=8,
            total_components=10,
        )
    )

    assert registry.count() == 1