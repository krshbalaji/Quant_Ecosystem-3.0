from quant_ecosystem.cognition.swarm import (
    OrchestrationResult,
)


def test_result_model():

    result = OrchestrationResult(
        request_id="REQ1",
        successful=True,
        stages_completed=3,
    )

    assert result.successful