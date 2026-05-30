from quant_ecosystem.cognition.swarm import (
    FederationCognitionWorkflowResult,
)


def test_workflow_result():

    result = (
        FederationCognitionWorkflowResult(
            workflow_name="wf",
            accepted=True,
        )
    )

    assert result.accepted is True