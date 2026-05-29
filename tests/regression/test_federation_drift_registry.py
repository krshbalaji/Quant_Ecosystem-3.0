from quant_ecosystem.cognition.swarm import (
    ArchitectureSnapshot,
    FederationDriftRegistry,
)


def test_drift_registry():

    registry = (
        FederationDriftRegistry()
    )

    registry.register(
        ArchitectureSnapshot(
            snapshot_id="S1",
            component_count=10,
        )
    )

    assert registry.count() == 1