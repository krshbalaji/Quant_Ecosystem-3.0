from quant_ecosystem.cognition.swarm import (
    FederationCognitionActionPlan,
    FederationCognitionActionStep,
    FederationCognitionExecutionCoordinator,
)


def test_execution_coordinator():

    plan = FederationCognitionActionPlan(
        action="EXECUTE_IMPROVEMENT_PLAN",
        steps=[
            FederationCognitionActionStep(
                sequence=1,
                description="analyze",
            )
        ],
    )

    report = (
        FederationCognitionExecutionCoordinator()
        .coordinate(plan)
    )

    assert report.execution_ready is True

    assert (
        report.workflow_name
        == "improvement_workflow"
    )