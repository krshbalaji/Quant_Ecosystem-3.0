from quant_ecosystem.cognition.swarm import (
    SubsystemAdapterResult,
)


def test_result_model():

    result = (
        SubsystemAdapterResult(
            request_id="REQ1",
            accepted=True,
            subsystem_name="risk_engine",
        )
    )

    assert result.accepted