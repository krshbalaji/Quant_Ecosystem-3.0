from quant_ecosystem.cognition.swarm import (
    GovernanceResolution,
)


def test_resolution_creation():

    resolution = GovernanceResolution(
        resolution_id="R1",
        outcome="approved",
        confidence=1.0,
        participant_count=2,
    )

    assert resolution.outcome == "approved"