from quant_ecosystem.cognition.swarm import (
    ArchitectureDensityMetric,
    FederationDensityRegistry,
)


def test_density_registry():

    registry = (
        FederationDensityRegistry()
    )

    registry.register(
        ArchitectureDensityMetric(
            category_name="governance",
            component_count=10,
        )
    )

    assert registry.count() == 1