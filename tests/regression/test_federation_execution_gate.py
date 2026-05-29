from quant_ecosystem.cognition.swarm import (
    ExecutionPolicy,
    ExecutionRequest,
    FederationExecutionGate,
)


def test_execution_gate():

    gate = FederationExecutionGate()

    result = gate.evaluate(
        ExecutionRequest(
            organism_id="alpha",
            execution_type="risk_budget",
            requested_amount=50,
        ),
        ExecutionPolicy(
            execution_type="risk_budget",
            maximum_authorization=75,
        ),
    )

    assert result.authorized