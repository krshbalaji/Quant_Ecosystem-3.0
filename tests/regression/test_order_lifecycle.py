import pytest

from quant_ecosystem.oms import (
    CanonicalOrderLifecycle,
    CanonicalExecutionEvent,
    CanonicalEventType,
    CanonicalOrderStatus,
    order_registry,
    execution_event_bus,
    order_state_machine,
    reconciliation_engine,
)


@pytest.fixture
def reset_oms():
    order_registry.clear()
    execution_event_bus.clear()
    yield
    order_registry.clear()
    execution_event_bus.clear()


def test_order_creation(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    assert order.status == CanonicalOrderStatus.NEW
    assert order.remaining_qty() == 10


def test_registry_register(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    order_registry.register(order)

    fetched = order_registry.get(order.order_id)

    assert fetched is not None


def test_duplicate_order_id(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    order_registry.register(order)

    with pytest.raises(ValueError):
        order_registry.register(order)


def test_state_submit(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    evt = CanonicalExecutionEvent(
        order_id=order.order_id,
        event_type=CanonicalEventType.ORDER_SUBMITTED,
    )

    order_state_machine.apply_event(order, evt)

    assert order.status == CanonicalOrderStatus.SUBMITTED


def test_state_ack(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

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

    assert order.status == CanonicalOrderStatus.ACKNOWLEDGED


def test_partial_fill(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

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

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.PARTIAL_FILL,
            qty=4,
            price=820.0,
        ),
    )

    assert order.status == CanonicalOrderStatus.PARTIALLY_FILLED
    assert order.filled_qty == 4


def test_full_fill(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

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

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.FULL_FILL,
            qty=10,
            price=821.0,
        ),
    )

    assert order.status == CanonicalOrderStatus.FILLED
    assert order.is_terminal()


def test_cancel_flow(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

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

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.CANCEL_REQUESTED,
        ),
    )

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.CANCELLED,
        ),
    )

    assert order.status == CanonicalOrderStatus.CANCELLED


def test_invalid_transition(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    with pytest.raises(ValueError):
        order_state_machine.apply_event(
            order,
            CanonicalExecutionEvent(
                order_id=order.order_id,
                event_type=CanonicalEventType.ORDER_ACK,
            ),
        )


def test_event_bus(reset_oms):
    hits = []

    def cb(evt):
        hits.append(evt.event_type)

    execution_event_bus.subscribe(
        CanonicalEventType.ORDER_ACK,
        cb,
    )

    execution_event_bus.publish(
        CanonicalExecutionEvent(
            order_id="abc",
            event_type=CanonicalEventType.ORDER_ACK,
        )
    )

    assert len(hits) == 1


def test_reconciliation_ack(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

    order_state_machine.apply_event(
        order,
        CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=CanonicalEventType.ORDER_SUBMITTED,
        ),
    )

    reconciliation_engine.reconcile(
        order,
        {
            "status": "OPEN",
            "filled_qty": 0,
            "avg_price": 0,
            "broker": "fyers",
        },
    )

    assert order.status == CanonicalOrderStatus.ACKNOWLEDGED


def test_reconciliation_fill(reset_oms):
    order = CanonicalOrderLifecycle(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
    )

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

    reconciliation_engine.reconcile(
        order,
        {
            "status": "FILLED",
            "filled_qty": 10,
            "avg_price": 823,
            "broker": "fyers",
        },
    )

    assert order.status == CanonicalOrderStatus.FILLED