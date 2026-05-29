from quant_ecosystem.cognition.swarm import (
    ArchitectureSnapshot,
    FederationDriftEngine,
    FederationDriftRegistry,
)


def test_drift_engine():

    registry = (
        FederationDriftRegistry()
    )

    registry.register(
        ArchitectureSnapshot(
            snapshot_id="S1",
            component_count=10,
        )
    )

    registry.register(
        ArchitectureSnapshot(
            snapshot_id="S2",
            component_count=15,
        )
    )

    report = (
        FederationDriftEngine()
        .evaluate(
            registry
        )
    )

    assert report.component_growth == 5
    assert report.growth_detected