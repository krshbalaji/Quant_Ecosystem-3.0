from quant_ecosystem.cognition.swarm import (
    ArchitectureEfficiencyMetric,
    FederationEfficiencyEngine,
    FederationEfficiencyRegistry,
)


def test_efficiency_engine():

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

    report = (
        FederationEfficiencyEngine()
        .evaluate(
            registry
        )
    )

    assert report.category_count == 1