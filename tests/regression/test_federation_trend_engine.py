from quant_ecosystem.cognition.swarm import (
    ArchitectureTrendDirection,
    ArchitectureTrendPoint,
    FederationTrendEngine,
    FederationTrendRegistry,
)


def test_trend_engine():

    registry = FederationTrendRegistry()

    registry.register(
        ArchitectureTrendPoint(
            sequence=1,
            component_count=10,
        )
    )

    registry.register(
        ArchitectureTrendPoint(
            sequence=2,
            component_count=15,
        )
    )

    report = (
        FederationTrendEngine()
        .evaluate(registry)
    )

    assert (
        report.trend_direction
        ==
        ArchitectureTrendDirection.GROWING
    )

    assert report.net_change == 5