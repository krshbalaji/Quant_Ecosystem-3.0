from quant_ecosystem.cognition.swarm import (
    FederationCognitionResponseReport,
    FederationCognitionActionPlanner,
)


def test_action_planner():

    response = FederationCognitionResponseReport(
        recommended_action=(
            "EXECUTE_IMPROVEMENT_PLAN"
        ),
        response_count=1,
    )

    plan = (
        FederationCognitionActionPlanner()
        .create_plan(response)
    )

    assert len(plan.steps) == 3