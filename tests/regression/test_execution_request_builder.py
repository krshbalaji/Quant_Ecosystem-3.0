from quant_ecosystem.cognition.swarm import (
    ExecutionRequestBuilder,
    FederationAction,
)


def test_request_builder():

    action = FederationAction(
        action_id="A1",
        action_type="governance",
        payload={},
    )

    request = (
        ExecutionRequestBuilder()
        .build(action)
    )

    assert request.request_id == "A1"