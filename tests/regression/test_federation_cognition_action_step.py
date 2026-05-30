from quant_ecosystem.cognition.swarm import (
    FederationCognitionActionStep,
)


def test_action_step():

    step = FederationCognitionActionStep(
        sequence=1,
        description="test",
    )

    assert step.sequence == 1