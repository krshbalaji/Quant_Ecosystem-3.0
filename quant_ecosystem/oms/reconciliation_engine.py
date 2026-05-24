"""
QE3 OMS reconciliation engine
Pack22
"""

from quant_ecosystem.oms.order_models import (
    CanonicalExecutionEvent,
    CanonicalEventType,
    CanonicalOrderStatus,
)

from quant_ecosystem.oms.order_state_machine import (
    order_state_machine,
)


BROKER_STATUS_MAP = {
    "NEW": CanonicalOrderStatus.NEW,
    "SUBMITTED": CanonicalOrderStatus.SUBMITTED,
    "OPEN": CanonicalOrderStatus.ACKNOWLEDGED,
    "ACKNOWLEDGED": CanonicalOrderStatus.ACKNOWLEDGED,
    "PARTIAL": CanonicalOrderStatus.PARTIALLY_FILLED,
    "PARTIALLY_FILLED": CanonicalOrderStatus.PARTIALLY_FILLED,
    "FILLED": CanonicalOrderStatus.FILLED,
    "CANCELLED": CanonicalOrderStatus.CANCELLED,
    "REJECTED": CanonicalOrderStatus.REJECTED,
    "FAILED": CanonicalOrderStatus.FAILED,
    "EXPIRED": CanonicalOrderStatus.EXPIRED,
}


class ReconciliationEngine:
    """
    Broker truth reconciliation
    """

    def normalize_status(self, broker_status: str):
        key = str(broker_status).strip().upper()

        if key not in BROKER_STATUS_MAP:
            raise ValueError(f"unknown broker status: {broker_status}")

        return BROKER_STATUS_MAP[key]

    def reconcile(self, local_order, broker_snapshot: dict):
        """
        broker_snapshot expected:
        {
            "status": "...",
            "filled_qty": int,
            "avg_price": float,
            "broker": "...",
        }
        """

        if local_order.is_terminal():
            return local_order

        broker_status = self.normalize_status(
            broker_snapshot.get("status", "UNKNOWN")
        )

        broker_filled = int(
            broker_snapshot.get("filled_qty", 0)
        )

        broker_price = float(
            broker_snapshot.get("avg_price", 0.0)
        )

        broker_name = broker_snapshot.get(
            "broker",
            local_order.broker,
        )

        # already synchronized
        if (
            local_order.status == broker_status
            and local_order.filled_qty == broker_filled
        ):
            return local_order

        # direct terminal reconciliation
        if broker_status == CanonicalOrderStatus.FILLED:
            event = CanonicalExecutionEvent(
                order_id=local_order.order_id,
                event_type=CanonicalEventType.FULL_FILL,
                qty=broker_filled,
                price=broker_price,
                broker=broker_name,
                payload=broker_snapshot,
            )
            return order_state_machine.apply_event(local_order, event)

        if broker_status == CanonicalOrderStatus.CANCELLED:
            event = CanonicalExecutionEvent(
                order_id=local_order.order_id,
                event_type=CanonicalEventType.CANCELLED,
                broker=broker_name,
                payload=broker_snapshot,
            )
            return order_state_machine.apply_event(local_order, event)

        if broker_status == CanonicalOrderStatus.REJECTED:
            event = CanonicalExecutionEvent(
                order_id=local_order.order_id,
                event_type=CanonicalEventType.REJECTED,
                broker=broker_name,
                payload=broker_snapshot,
            )
            return order_state_machine.apply_event(local_order, event)

        # partial fill reconciliation
        if broker_status == CanonicalOrderStatus.PARTIALLY_FILLED:
            delta = broker_filled - local_order.filled_qty

            if delta > 0:
                event = CanonicalExecutionEvent(
                    order_id=local_order.order_id,
                    event_type=CanonicalEventType.PARTIAL_FILL,
                    qty=delta,
                    price=broker_price,
                    broker=broker_name,
                    payload=broker_snapshot,
                )
                return order_state_machine.apply_event(local_order, event)

        # acknowledgment reconciliation
        if broker_status == CanonicalOrderStatus.ACKNOWLEDGED:
            if local_order.status in {
                CanonicalOrderStatus.NEW,
                CanonicalOrderStatus.SUBMITTED,
            }:
                event = CanonicalExecutionEvent(
                    order_id=local_order.order_id,
                    event_type=CanonicalEventType.ORDER_ACK,
                    broker=broker_name,
                    payload=broker_snapshot,
                )
                return order_state_machine.apply_event(local_order, event)

        return local_order


reconciliation_engine = ReconciliationEngine()