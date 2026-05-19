import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from broker.paper_broker import PaperBroker
from quant_ecosystem.contracts.order_intent import OrderIntent


PAPER_MODES = {"PAPER", "SIM", "SIMULATED", "DRY_RUN"}
LIVE_MODES = {"LIVE", "REAL"}
VALID_SIDES = {"BUY", "SELL"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_order_intent(order_intent: OrderIntent | Mapping[str, Any]) -> OrderIntent:
    if isinstance(order_intent, OrderIntent):
        return order_intent

    if isinstance(order_intent, Mapping):
        return OrderIntent.from_mapping(order_intent)

    raise TypeError("order_intent must be OrderIntent or mapping")


def _log_order(order: OrderIntent, decision: str, reason: str = "") -> None:
    data = order.to_dict()
    event = {
        "time": _utc_now(),
        "symbol": data["symbol"],
        "side": data["side"],
        "qty": data["qty"],
        "profile": data["profile"],
        "source": data["source"],
        "decision": decision,
    }

    if reason:
        event["reason"] = reason

    print(json.dumps(event, separators=(",", ":"), sort_keys=True))


def validate_order(order_intent: OrderIntent | Mapping[str, Any]) -> Dict[str, Any]:
    order = _as_order_intent(order_intent)
    data = order.to_dict()
    errors = []

    if not data["symbol"]:
        errors.append("symbol is required")

    if data["side"] not in VALID_SIDES:
        errors.append("side must be BUY or SELL")

    if data["qty"] <= 0:
        errors.append("qty must be > 0")

    if not data["profile"]:
        errors.append("profile is required")

    if not data["source"]:
        errors.append("source is required")

    if errors:
        _log_order(order, "rejected", "; ".join(errors))
        return {
            "ok": False,
            "decision": "rejected",
            "errors": errors,
            "order": data,
        }

    return {
        "ok": True,
        "decision": "validated",
        "errors": [],
        "order": data,
    }


class UnifiedBrokerRouter:
    """Canonical future execution gateway.

    This facade is intentionally additive. It does not replace or rewire legacy
    broker modules yet; callers can opt in by submitting canonical OrderIntent
    objects or compatible dictionaries.
    """

    def __init__(
        self,
        mode: str = "PAPER",
        paper_broker: Optional[Any] = None,
        live_broker: Optional[Any] = None,
    ):
        self.mode = str(mode or "PAPER").upper()
        self.paper_broker = paper_broker or PaperBroker()
        self.live_broker = live_broker

    def submit(self, order_intent: OrderIntent | Mapping[str, Any]) -> Dict[str, Any]:
        order = _as_order_intent(order_intent)
        validation = validate_order(order)

        if not validation["ok"]:
            return validation

        if self.mode in PAPER_MODES:
            return self.paper_submit(order)

        if self.mode in LIVE_MODES:
            return self.live_submit(order)

        _log_order(order, "rejected", f"unsupported mode: {self.mode}")
        return {
            "ok": False,
            "decision": "rejected",
            "reason": f"unsupported mode: {self.mode}",
            "order": order.to_dict(),
        }

    def paper_submit(self, order_intent: OrderIntent | Mapping[str, Any]) -> Dict[str, Any]:
        order = _as_order_intent(order_intent)
        validation = validate_order(order)

        if not validation["ok"]:
            return validation

        data = order.to_dict()
        result = self.paper_broker.place_order(
            data["symbol"],
            data["side"],
            data["qty"],
        )
        _log_order(order, "executed")

        return {
            "ok": True,
            "decision": "executed",
            "mode": "PAPER",
            "order": data,
            "broker_result": result,
        }

    def live_submit(self, order_intent: OrderIntent | Mapping[str, Any]) -> Dict[str, Any]:
        order = _as_order_intent(order_intent)
        validation = validate_order(order)

        if not validation["ok"]:
            return validation

        data = order.to_dict()

        if self.live_broker is None:
            _log_order(order, "rejected", "live broker not configured")
            return {
                "ok": False,
                "decision": "rejected",
                "mode": "LIVE",
                "reason": "live broker not configured",
                "order": data,
            }

        try:
            result = self.live_broker.place_order(
                data["symbol"],
                data["side"],
                data["qty"],
                order_type=data["order_type"],
                profile=data["profile"],
                reason=data["reason"],
                approval_id=data["approval_id"],
                source=data["source"],
                metadata=data["metadata"],
            )
        except Exception as exc:
            _log_order(order, "rejected", str(exc))
            return {
                "ok": False,
                "decision": "rejected",
                "mode": "LIVE",
                "reason": str(exc),
                "order": data,
            }

        _log_order(order, "executed")
        return {
            "ok": True,
            "decision": "executed",
            "mode": "LIVE",
            "order": data,
            "broker_result": result,
        }


def submit(order_intent: OrderIntent | Mapping[str, Any], mode: str = "PAPER") -> Dict[str, Any]:
    return UnifiedBrokerRouter(mode=mode).submit(order_intent)


def paper_submit(order_intent: OrderIntent | Mapping[str, Any]) -> Dict[str, Any]:
    return UnifiedBrokerRouter(mode="PAPER").paper_submit(order_intent)


def live_submit(
    order_intent: OrderIntent | Mapping[str, Any],
    live_broker: Optional[Any] = None,
) -> Dict[str, Any]:
    return UnifiedBrokerRouter(mode="LIVE", live_broker=live_broker).live_submit(order_intent)
