from quant_ecosystem.cognition.swarm import (
    FederationCognitionWorkflowRequest,
)


def test_workflow_request():

    request = (
        FederationCognitionWorkflowRequest(
            workflow_name="wf",
            action="act",
        )
    )

    assert request.workflow_name == "wf"