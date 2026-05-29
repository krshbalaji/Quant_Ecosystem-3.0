from quant_ecosystem.cognition.swarm import (
    ArchitectureDensityMetric,
    FederationDensityEngine,
    FederationDensityRegistry,
)


def test_density_engine():

    registry = (
        FederationDensityRegistry()
    )

    registry.register(
        ArchitectureDensityMetric(
            category_name="governance",
            component_count=10,
        )
    )

    registry.register(
        ArchitectureDensityMetric(
            category_name="topology",
            component_count=5,
        )
    )

    report = (
        FederationDensityEngine()
        .evaluate(
            registry
        )
    )

    assert (
        report.densest_category
        == "governance"
    )

    assert (
        report.component_count
        == 10
    )