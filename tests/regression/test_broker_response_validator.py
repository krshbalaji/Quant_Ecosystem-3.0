import pytest

from quant_ecosystem.execution.broker_response_validator import (
    validate_live_broker_response,
    BrokerResponseError,
)


def test_live_broker_rejects_error_payload():
    with pytest.raises(BrokerResponseError):
        validate_live_broker_response({
            "s": "error",
            "message": "Rejected"
        })


def test_live_broker_rejects_missing_order_id():
    with pytest.raises(BrokerResponseError):
        validate_live_broker_response({
            "s": "ok"
        })


def test_live_broker_accepts_valid_payload():
    payload = {
        "s": "ok",
        "id": "ABC123"
    }

    result = validate_live_broker_response(payload)

    assert result["id"] == "ABC123"