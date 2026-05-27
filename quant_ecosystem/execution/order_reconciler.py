import time

from quant_ecosystem.execution.order_status_normalizer import (
    OrderStatusNormalizer,
)


class OrderReconciler:
    """
    Institutional reconciliation governance.
    """

    TERMINAL = {
        "FILLED",
        "REJECTED",
        "CANCELLED",
        "EXPIRED",
        "DEADLETTER",
    }

    STALE_TIMEOUT = 60

    def __init__(
        self,
        poll_interval=2,
        timeout=20,
    ):
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.normalizer = (
            OrderStatusNormalizer()
        )

    def wait_for_final_state(
        self,
        broker_name,
        broker,
        order_id,
    ):
        start = time.time()

        while True:
            elapsed = (
                time.time() - start
            )

            if elapsed > self.STALE_TIMEOUT:
                return {
                    "status": "DEADLETTER",
                    "order_id": order_id,
                }

            if elapsed > self.timeout:
                raise RuntimeError(
                    "LIVE reconciliation timeout"
                )

            raw = self.poll_order_status(
                broker,
                order_id,
            )

            normalized = (
                self.normalizer.normalize(
                    broker_name,
                    raw,
                )
            )

            if (
                normalized["status"]
                in self.TERMINAL
            ):
                return normalized

            time.sleep(
                self.poll_interval
            )

    def poll_order_status(
        self,
        broker,
        order_id,
    ):
        if hasattr(
            broker,
            "get_order_status",
        ):
            return broker.get_order_status(
                order_id
            )

        if hasattr(
            broker,
            "get_orders",
        ):
            orders = broker.get_orders()

            if isinstance(
                orders,
                list,
            ):
                for order in orders:
                    oid = str(
                        order.get("id")
                        or
                        order.get("order_id")
                        or
                        ""
                    )

                    if oid == str(order_id):
                        return order

        raise RuntimeError(
            "Broker does not support order reconciliation"
        )