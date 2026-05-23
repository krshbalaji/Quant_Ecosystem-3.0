from __future__ import annotations


class BrokerResponseError(RuntimeError):
    pass


def validate_live_broker_response(result):
    if not isinstance(result, dict):
        raise BrokerResponseError(
            f"LIVE broker invalid response type: {type(result).__name__}"
        )

    if str(result.get("s", "")).lower() == "error":
        raise BrokerResponseError(
            result.get("message", "LIVE broker rejected order")
        )

    order_id = result.get("order_id") or result.get("id")

    if not order_id:
        raise BrokerResponseError(
            f"LIVE broker returned no order id: {result}"
        )

    return result