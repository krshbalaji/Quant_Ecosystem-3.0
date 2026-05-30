from quant_ecosystem.cognition.swarm import (
    FederationCognitionExecutionReport,
    FederationCognitionWorkflowAdapter,
)


def test_workflow_adapter():

    report = (
        FederationCognitionExecutionReport(
            workflow_name="growth_workflow",
            action="ACT",
            execution_ready=True,
        )
    )

    result = (
        FederationCognitionWorkflowAdapter()
        .adapt(report)
    )

    assert result.accepted is True

    assert (
        result.workflow_name
        == "growth_workflow"
    )