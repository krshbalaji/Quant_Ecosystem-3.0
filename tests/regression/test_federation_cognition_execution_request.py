from quant_ecosystem.cognition.swarm import (
    FederationCognitionExecutionRequest,
)


def test_execution_request():

    request = (
        FederationCognitionExecutionRequest(
            action="TEST",
            workflow_name="wf",
        )
    )

    assert request.workflow_name == "wf"