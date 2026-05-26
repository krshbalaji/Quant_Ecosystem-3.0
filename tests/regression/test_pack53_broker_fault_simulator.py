from quant_ecosystem.execution.chaos.broker_fault_simulator import (
    BrokerFaultSimulator,
)


def test_false_success_fault():
    result = BrokerFaultSimulator.false_success()

    assert result["status"] == "SUCCESS"
    assert result["order_id"] is None


def test_malformed_success_fault():
    result = BrokerFaultSimulator.malformed_success()

    assert result["ok"] is True


def test_partial_fill_fault():
    result = BrokerFaultSimulator.partial_fill_missing_qty()

    assert result["status"] == "PARTIAL"


def test_duplicate_ack_fault():
    result = BrokerFaultSimulator.duplicate_ack()

    assert result["order_id"] == "DUPLICATE-ACK-001"


def test_reject_with_success_flag():
    result = BrokerFaultSimulator.reject_with_success_flag()

    assert result["rejected"] is True