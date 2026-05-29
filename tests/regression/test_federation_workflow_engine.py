from quant_ecosystem.cognition.swarm import (
    FederationWorkflowEngine,
    WorkflowDefinition,
)


def test_workflow_execution():

    engine = (
        FederationWorkflowEngine()
    )

    result = engine.execute(
        WorkflowDefinition(
            workflow_id="WF1",
            stages=[
                "governance",
                "policy",
                "allocation",
            ],
        )
    )

    assert result.successful
    assert len(
        result.stage_results
    ) == 3