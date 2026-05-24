"""
QE3 OMS order state machine
Pack22
"""

from datetime import datetime

from quant_ecosystem.oms.order_models import (
    CanonicalOrderStatus,
    CanonicalEventType,
)


VALID_TRANSITIONS = {
    CanonicalOrderStatus.NEW: {
        CanonicalOrderStatus.SUBMITTED,
        CanonicalOrderStatus.REJECTED,
        CanonicalOrderStatus.FAILED,
    },

    CanonicalOrderStatus.SUBMITTED: {
        CanonicalOrderStatus.ACKNOWLEDGED,
        CanonicalOrderStatus.REJECTED,
        CanonicalOrderStatus.FAILED,
    },

    CanonicalOrderStatus.ACKNOWLEDGED: {
        CanonicalOrderStatus.PARTIALLY_FILLED,
        CanonicalOrderStatus.FILLED,
        CanonicalOrderStatus.CANCEL_PENDING,
        CanonicalOrderStatus.REJECTED,
        CanonicalOrderStatus.FAILED,
    },

    CanonicalOrderStatus.PARTIALLY_FILLED: {
        CanonicalOrderStatus.PARTIALLY_FILLED,
        CanonicalOrderStatus.FILLED,
        CanonicalOrderStatus.CANCEL_PENDING,
        CanonicalOrderStatus.FAILED,
    },

    CanonicalOrderStatus.CANCEL_PENDING: {
        CanonicalOrderStatus.CANCELLED,
        CanonicalOrderStatus.FILLED,
        CanonicalOrderStatus.PARTIALLY_FILLED,
    },
}


class OrderStateMachine:
    def can_transition(self, current, nxt):
        allowed = VALID_TRANSITIONS.get(current, set())
        return nxt in allowed

    def transition(self, order, nxt):
        if order.is_terminal():
            raise ValueError("terminal order cannot transition")

        if not self.can_transition(order.status, nxt):
            raise ValueError(
                f"invalid transition: {order.status} -> {nxt}"
            )

        order.status = nxt
        order.updated_at = datetime.utcnow()

        return order

    def apply_event(self, order, event):
        if event.event_type == CanonicalEventType.ORDER_SUBMITTED:
            return self.transition(order, CanonicalOrderStatus.SUBMITTED)

        elif event.event_type == CanonicalEventType.ORDER_ACK:
            return self.transition(order, CanonicalOrderStatus.ACKNOWLEDGED)

        elif event.event_type == CanonicalEventType.PARTIAL_FILL:
            order.filled_qty += event.qty

            if order.filled_qty >= order.qty:
                order.filled_qty = order.qty
                order.avg_fill_price = event.price
                return self.transition(order, CanonicalOrderStatus.FILLED)

            order.avg_fill_price = event.price
            return self.transition(
                order,
                CanonicalOrderStatus.PARTIALLY_FILLED,
            )

        elif event.event_type == CanonicalEventType.FULL_FILL:
            order.filled_qty = order.qty
            order.avg_fill_price = event.price
            return self.transition(order, CanonicalOrderStatus.FILLED)

        elif event.event_type == CanonicalEventType.CANCEL_REQUESTED:
            return self.transition(
                order,
                CanonicalOrderStatus.CANCEL_PENDING,
            )

        elif event.event_type == CanonicalEventType.CANCELLED:
            return self.transition(
                order,
                CanonicalOrderStatus.CANCELLED,
            )

        elif event.event_type == CanonicalEventType.REJECTED:
            return self.transition(
                order,
                CanonicalOrderStatus.REJECTED,
            )

        elif event.event_type == CanonicalEventType.ERROR:
            return self.transition(
                order,
                CanonicalOrderStatus.FAILED,
            )

        raise ValueError("unknown event")
        

order_state_machine = OrderStateMachine()