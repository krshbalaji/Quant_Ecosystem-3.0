from quant_ecosystem.cognition.swarm import (
    ArchitectureTrendPoint,
    FederationTrendRegistry,
)


def test_trend_registry():

    registry = FederationTrendRegistry()

    registry.register(
        ArchitectureTrendPoint(
            sequence=1,
            component_count=10,
        )
    )

    assert registry.count() == 1