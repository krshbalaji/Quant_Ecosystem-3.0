"""
QE3 Event Ingestion Engine
Pack24
"""

from quant_ecosystem.events.broker_event_models import (
    CanonicalBrokerEventType,
)

from quant_ecosystem.events.event_registry import (
    event_registry,
)

from quant_ecosystem.oms import (
    order_registry,
    order_state_machine,
    CanonicalExecutionEvent,
    CanonicalEventType,
)

from quant_ecosystem.accounting import (
    CanonicalTradeFill,
    accounting_engine,
)


EVENT_TO_OMS = {
    CanonicalBrokerEventType.ORDER_ACK:
        CanonicalEventType.ORDER_ACK,

    CanonicalBrokerEventType.PARTIAL_FILL:
        CanonicalEventType.PARTIAL_FILL,

    CanonicalBrokerEventType.FULL_FILL:
        CanonicalEventType.FULL_FILL,

    CanonicalBrokerEventType.CANCELLED:
        CanonicalEventType.CANCELLED,

    CanonicalBrokerEventType.REJECTED:
        CanonicalEventType.REJECTED,

    CanonicalBrokerEventType.ERROR:
        CanonicalEventType.ERROR,
}


class EventIngestionEngine:
    """
    Canonical broker event router
    """

    def ingest(self, broker_event):
        if event_registry.seen(broker_event.event_id):
            return {
                "status": "duplicate_ignored"
            }

        event_registry.mark_seen(broker_event.event_id)

        if broker_event.event_type in {
            CanonicalBrokerEventType.HEARTBEAT,
            CanonicalBrokerEventType.DISCONNECT,
            CanonicalBrokerEventType.RECONNECT,
            CanonicalBrokerEventType.MODIFIED,
        }:
            return {
                "status": "non_execution_event_accepted"
            }

        order = order_registry.get(broker_event.order_id)

        if not order:
            raise ValueError(
                f"unknown OMS order: {broker_event.order_id}"
            )

        oms_event_type = EVENT_TO_OMS.get(
            broker_event.event_type
        )

        if not oms_event_type:
            raise ValueError(
                f"unsupported broker event: {broker_event.event_type}"
            )

        oms_event = CanonicalExecutionEvent(
            order_id=order.order_id,
            event_type=oms_event_type,
            qty=broker_event.qty,
            price=broker_event.price,
            broker=broker_event.broker,
            payload=broker_event.payload,
        )

        order_state_machine.apply_event(
            order,
            oms_event,
        )

        accounting_snapshot = None

        if broker_event.event_type in {
            CanonicalBrokerEventType.PARTIAL_FILL,
            CanonicalBrokerEventType.FULL_FILL,
        }:
            fill = CanonicalTradeFill(
                broker=order.broker,
                symbol=order.symbol,
                side=order.side,
                qty=broker_event.qty,
                price=broker_event.price,
                order_id=order.order_id,
                metadata=broker_event.payload,
            )

            accounting_snapshot = accounting_engine.process_fill(
                fill
            )

        return {
            "status": "processed",
            "oms_order_id": order.order_id,
            "order_status": order.status.value,
            "filled_qty": order.filled_qty,
            "accounting": (
                None
                if accounting_snapshot is None
                else {
                    "realized_pnl":
                        accounting_snapshot.realized_pnl,
                    "unrealized_pnl":
                        accounting_snapshot.unrealized_pnl,
                    "gross_pnl":
                        accounting_snapshot.gross_pnl,
                    "net_pnl":
                        accounting_snapshot.net_pnl,
                    "fills_processed":
                        accounting_snapshot.fills_processed,
                }
            ),
        }

    def clear(self):
        event_registry.clear()


event_ingestion_engine = EventIngestionEngine()