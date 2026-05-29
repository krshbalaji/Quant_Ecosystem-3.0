from quant_ecosystem.cognition.swarm import (
    ExecutionAuthorization,
)


def test_execution_authorization_model():

    authorization = ExecutionAuthorization(
        organism_id="alpha",
        execution_type="capital",
        authorized=True,
        approved_amount=10,
    )

    assert authorization.authorized