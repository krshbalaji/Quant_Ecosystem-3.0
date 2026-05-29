from quant_ecosystem.cognition.swarm import (
    ExecutionAuthorizationEngine,
    ExecutionPolicy,
    ExecutionRequest,
)


def test_authorization_limit():

    engine = ExecutionAuthorizationEngine()

    result = engine.authorize(
        ExecutionRequest(
            organism_id="alpha",
            execution_type="capital",
            requested_amount=200,
        ),
        ExecutionPolicy(
            execution_type="capital",
            maximum_authorization=100,
        ),
    )

    assert result.authorized
    assert result.approved_amount == 100