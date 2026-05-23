from typing import Dict, Any


class OrderStatusNormalizer:
    """
    Normalize broker-specific order payloads into QE3 canonical format.
    Supports multi-broker / multi-market execution.
    """

    STATUS_MAP = {
        "filled": "FILLED",
        "complete": "FILLED",
        "executed": "FILLED",
        "success": "FILLED",

        "partial": "PARTIAL",
        "partially_filled": "PARTIAL",

        "pending": "PENDING",
        "open": "PENDING",
        "new": "PENDING",

        "rejected": "REJECTED",
        "cancelled": "REJECTED",
        "canceled": "REJECTED",
        "error": "REJECTED",
    }

    def normalize(
        self,
        broker_name: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        if not isinstance(payload, dict):
            raise RuntimeError("Broker payload must be dict")

        broker = (broker_name or "").lower().strip()

        if "fyers" in broker:
            return self._normalize_fyers(payload)

        if "coinswitch" in broker:
            return self._normalize_coinswitch(payload)

        if "viewtrade" in broker:
            return self._normalize_viewtrade(payload)

        return self._normalize_generic(payload)

    def _normalize_fyers(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        status = str(
            payload.get("status")
            or payload.get("s")
            or "pending"
        ).lower()

        return {
            "status": self.STATUS_MAP.get(status, "PENDING"),
            "filled_qty": int(payload.get("filledQty", 0) or 0),
            "remaining_qty": int(payload.get("remainingQuantity", 0) or 0),
            "avg_price": float(payload.get("tradedPrice", 0.0) or 0.0),
            "order_id": str(
                payload.get("id")
                or payload.get("order_id")
                or ""
            ),
        }

    def _normalize_coinswitch(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        status = str(payload.get("status", "pending")).lower()

        return {
            "status": self.STATUS_MAP.get(status, "PENDING"),
            "filled_qty": int(payload.get("executed_quantity", 0) or 0),
            "remaining_qty": int(payload.get("remaining_quantity", 0) or 0),
            "avg_price": float(payload.get("average_price", 0.0) or 0.0),
            "order_id": str(payload.get("order_id", "")),
        }

    def _normalize_viewtrade(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        status = str(
            payload.get("order_status", "pending")
        ).lower()

        return {
            "status": self.STATUS_MAP.get(status, "PENDING"),
            "filled_qty": int(payload.get("filled_quantity", 0) or 0),
            "remaining_qty": int(payload.get("remaining_quantity", 0) or 0),
            "avg_price": float(payload.get("avg_execution_price", 0.0) or 0.0),
            "order_id": str(payload.get("order_id", "")),
        }

    def _normalize_generic(
        self,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:

        status = str(payload.get("status", "pending")).lower()

        return {
            "status": self.STATUS_MAP.get(status, "PENDING"),
            "filled_qty": int(payload.get("filled_qty", 0) or 0),
            "remaining_qty": int(payload.get("remaining_qty", 0) or 0),
            "avg_price": float(payload.get("avg_price", 0.0) or 0.0),
            "order_id": str(
                payload.get("order_id")
                or payload.get("id")
                or ""
            ),
        }