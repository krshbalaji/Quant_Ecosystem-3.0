import pytest

from quant_ecosystem.execution.contracts.broker_response_validator import (
    BrokerResponseValidator,
)

from quant_ecosystem.execution.chaos.broker_fault_simulator import (
    BrokerFaultSimulator,
)


def test_valid_trade():
    validator = BrokerResponseValidator()

    result = validator.validate(
        {
            "status": "TRADE",
            "order_id": "OK123",
        }
    )

    assert result["order_id"] == "OK123"


def test_false_success_blocked():
    validator = BrokerResponseValidator()

    with pytest.raises(RuntimeError):
        validator.validate(
            BrokerFaultSimulator.false_success()
        )


def test_malformed_blocked():
    validator = BrokerResponseValidator()

    with pytest.raises(RuntimeError):
        validator.validate(
            BrokerFaultSimulator.malformed_success()
        )


def test_partial_missing_qty_blocked():
    validator = BrokerResponseValidator()

    with pytest.raises(RuntimeError):
        validator.validate(
            BrokerFaultSimulator.partial_fill_missing_qty()
        )


def test_stale_ack_blocked():
    validator = BrokerResponseValidator()

    with pytest.raises(RuntimeError):
        validator.validate(
            BrokerFaultSimulator.stale_ack()
        )


def test_contradictory_success_blocked():
    validator = BrokerResponseValidator()

    with pytest.raises(RuntimeError):
        validator.validate(
            BrokerFaultSimulator.reject_with_success_flag()
        )