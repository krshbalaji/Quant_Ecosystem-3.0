from quant_ecosystem.cognition.swarm import (
    FederationCognitionResponse,
)


def test_response():

    response = FederationCognitionResponse(
        action="ACT",
        rationale="reason",
    )

    assert response.action == "ACT"