from quant_ecosystem.cognition.swarm import (
    ExecutionAuthorization,
)


def test_execution_authorization():

    authorization = (
        ExecutionAuthorization(
            organism_id="ORG1",
            execution_type="allocation",
            authorized=True,
            approved_amount=1000.0,
        )
    )

    assert authorization.authorized