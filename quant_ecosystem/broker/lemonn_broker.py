from typing import Any, Dict, List, Optional

from quant_ecosystem.broker.base_broker import BaseBroker
from quant_ecosystem.broker.broker_capabilities import LEMONN_CAPABILITIES


class LemonnBroker(BaseBroker):
    """
    QE3 Lemonn adapter (Pack17 capability contract version).

    Capability-aware scaffold.
    Live integration can replace internals later without router rewrite.
    """

    capabilities = LEMONN_CAPABILITIES

    def __init__(self, config=None, **kwargs):
        self._config = config
        self.connected = True
        self.orders: List[Dict[str, Any]] = []
        self.positions: List[Dict[str, Any]] = []

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
            "order_id": f"LEMONN-{len(self.orders)+1}",
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

    from typing import Optional
    def modify_order(
        self,
        order_id: str,
        qty: int | None = None,
        price: float | None = None,
    ):
        new_qty = qty if qty is not None else 0
        new_price = price if price is not None else 0.0
        return {
            "status": "MODIFIED",
            "order_id": order_id,
            "qty": new_qty,
            "price": new_price,
        }

    # =========================================================
    # RECONCILIATION
    # =========================================================

    def get_order_status(self, order_id: str):
        for order in self.orders:
            if order["order_id"] == order_id:
                return order

        raise RuntimeError(
            f"Lemonn order not found: {order_id}"
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
            "broker": "lemonn",
            "healthy": True,
            "details": "adapter scaffold healthy",
        }