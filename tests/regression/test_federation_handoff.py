from quant_ecosystem.cognition.swarm import (
    FederationHandoff,
)


def test_handoff_model():

    handoff = FederationHandoff(
        action_id="A1",
        target_system="risk_engine",
        accepted=True,
    )

    assert handoff.accepted