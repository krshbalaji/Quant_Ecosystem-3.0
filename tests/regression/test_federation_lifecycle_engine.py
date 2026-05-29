from quant_ecosystem.cognition.swarm import (
    FederationLifecycleEngine,
    FederationLifecycleTracker,
    InitiativeLifecycleRecord,
    InitiativeLifecycleState,
)


def test_lifecycle_engine():

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

    report = (
        FederationLifecycleEngine()
        .evaluate(
            tracker
        )
    )

    assert report.active_records == 1