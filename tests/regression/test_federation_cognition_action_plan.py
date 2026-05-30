from quant_ecosystem.cognition.swarm import (
    FederationCognitionActionPlan,
    FederationCognitionActionStep,
)


def test_action_plan():

    plan = FederationCognitionActionPlan(
        action="TEST",
        steps=[
            FederationCognitionActionStep(
                sequence=1,
                description="step",
            )
        ],
    )

    assert len(plan.steps) == 1