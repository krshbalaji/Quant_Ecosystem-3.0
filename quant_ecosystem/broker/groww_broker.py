from typing import Any, Dict, List, Optional

from quant_ecosystem.broker.base_broker import BaseBroker
from quant_ecosystem.broker.broker_capabilities import GROWW_CAPABILITIES


class GrowwBroker(BaseBroker):
    """
    QE3 Groww adapter (Pack17 capability contract version).

    Adapter scaffold until live API integration is finalized.
    Router can safely reason about capabilities immediately.
    """

    client: Any
    capabilities = GROWW_CAPABILITIES

    def __init__(self, config=None, **kwargs):
        self._config = config
        self.connected = True
        self.orders: List[Dict[str, Any]] = []
        self.positions: List[Dict[str, Any]] = []
        self.client: Any = kwargs.get("client")
    # =========================================================
    # EXECUTION
    # =========================================================

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        order = {
            "order_id": f"GROWW-{len(self.orders)+1}",
            "status": "FILLED",
            "filled_qty": qty,
            "remaining_qty": 0,
            "avg_price": price,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "fee": fee,
            "meta": meta or {},
        }

        self.orders.append(order)
        return order

    def cancel_order(self, order_id: str):
        return {
            "status": "CANCELLED",
            "order_id": order_id,
        }

    def modify_order(
        self,
        order_id: str,
        qty: int | None = None,
        price: float | None = None,
    ):
        return self.client.modify_order(
            order_id=order_id,
            qty=qty,
            price=price,
        )

    # =========================================================
    # RECONCILIATION
    # =========================================================

    def get_order_status(self, order_id: str):
        for order in self.orders:
            if order["order_id"] == order_id:
                return order

        raise RuntimeError(
            f"Groww order not found: {order_id}"
        )

    def get_order_history(self):
        return self.orders.copy()

    # =========================================================
    # ACCOUNT
    # =========================================================

    def get_positions(self):
        return self.positions.copy()

    def get_balance(self):
        return {
            "available_cash": 0.0,
            "currency": "INR",
        }

    def get_holdings(self):
        return []

    def get_ltp(self, symbol: str):
        return {
            "symbol": symbol,
            "ltp": 0.0,
        }

    def get_orderbook(self):
        return self.orders.copy()

    # =========================================================
    # HEALTH
    # =========================================================

    def health_check(self):
        return {
            "broker": "groww",
            "healthy": True,
            "details": "adapter scaffold healthy",
        }