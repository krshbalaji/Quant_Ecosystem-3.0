from quant_ecosystem.cognition.swarm import (
    RouterExecutionResult,
)


def test_result_model():

    result = RouterExecutionResult(
        request_id="REQ-1",
        accepted=True,
        adapter_id="adapter",
    )

    assert result.accepted