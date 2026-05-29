from quant_ecosystem.cognition.swarm import (
    FederationLifecycleTracker,
    InitiativeLifecycleRecord,
    InitiativeLifecycleState,
)


def test_lifecycle_tracker():

    tracker = (
        FederationLifecycleTracker()
    )

    tracker.register(
        InitiativeLifecycleRecord(
            initiative_id="INIT1",
            state=(
                InitiativeLifecycleState.ACTIVE
            ),
        )
    )

    assert tracker.count() == 1
    assert tracker.active_count() == 1