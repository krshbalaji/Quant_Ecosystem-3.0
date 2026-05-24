import pytest

from quant_ecosystem.events import (
    CanonicalBrokerEvent,
    CanonicalBrokerEventType,
    BrokerEventSource,
    event_ingestion_engine,
    stream_dispatcher,
)

from quant_ecosystem.oms import (
    CanonicalOrderLifecycle,
    order_registry,
    order_state_machine,
    CanonicalExecutionEvent,
    CanonicalEventType,
    CanonicalOrderStatus,
)

from quant_ecosystem.accounting import (
    accounting_engine,
)


@pytest.fixture
def reset_state():
    order_registry.clear()
    accounting_engine.clear()
    event_ingestion_engine.clear()
    yield
    order_registry.clear()
    accounting_engine.clear()
    event_ingestion_engine.clear()


def create_ack_order():
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    order_registry.register(order)

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.ORDER_SUBMITTED,
        ),
    )

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.ORDER_ACK,
        ),
    )

    return order


def test_ack_event(reset_state):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    order_registry.register(order)

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.ORDER_SUBMITTED,
        ),
    )

    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.ORDER_ACK,
        source=BrokerEventSource.WEBHOOK,
        order_id=order.order_id,
    )

    result = event_ingestion_engine.ingest(evt)

    assert result["status"] == "processed"
    assert order.status == CanonicalOrderStatus.ACKNOWLEDGED


def test_partial_fill(reset_state):
    order = create_ack_order()

    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.PARTIAL_FILL,
        source=BrokerEventSource.WEBHOOK,
        order_id=order.order_id,
        qty=4,
        price=820.0,
    )

    result = event_ingestion_engine.ingest(evt)

    assert result["status"] == "processed"
    assert order.status == CanonicalOrderStatus.PARTIALLY_FILLED
    assert order.filled_qty == 4


def test_full_fill(reset_state):
    order = create_ack_order()

    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.FULL_FILL,
        source=BrokerEventSource.WEBHOOK,
        order_id=order.order_id,
        qty=10,
        price=821.0,
    )

    result = event_ingestion_engine.ingest(evt)

    assert result["status"] == "processed"
    assert order.status == CanonicalOrderStatus.FILLED


def test_duplicate_event(reset_state):
    order = create_ack_order()

    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.PARTIAL_FILL,
        source=BrokerEventSource.WEBHOOK,
        order_id=order.order_id,
        qty=2,
        price=820.0,
        event_id="dup1",
    )

    first = event_ingestion_engine.ingest(evt)
    second = event_ingestion_engine.ingest(evt)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate_ignored"


def test_unknown_order(reset_state):
    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.ORDER_ACK,
        source=BrokerEventSource.WEBHOOK,
        order_id="ghost",
    )

    with pytest.raises(ValueError):
        event_ingestion_engine.ingest(evt)


def test_accounting_on_fill(reset_state):
    order = create_ack_order()

    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.FULL_FILL,
        source=BrokerEventSource.WEBHOOK,
        order_id=order.order_id,
        qty=10,
        price=100.0,
    )

    result = event_ingestion_engine.ingest(evt)

    assert result["accounting"] is not None
    assert result["accounting"]["fills_processed"] == 1


def test_stream_heartbeat(reset_state):
    result = stream_dispatcher.heartbeat("fyers")
    assert result["status"] == "non_execution_event_accepted"


def test_stream_disconnect(reset_state):
    result = stream_dispatcher.disconnect("fyers")
    assert result["status"] == "non_execution_event_accepted"


def test_stream_reconnect(reset_state):
    result = stream_dispatcher.reconnect("fyers")
    assert result["status"] == "non_execution_event_accepted"


def test_rejected_event(reset_state):
    order = create_ack_order()

    evt = CanonicalBrokerEvent(
        broker="fyers",
        event_type=CanonicalBrokerEventType.REJECTED,
        source=BrokerEventSource.WEBHOOK,
        order_id=order.order_id,
    )

    result = event_ingestion_engine.ingest(evt)

    assert result["status"] == "processed"
    assert order.status == CanonicalOrderStatus.REJECTED