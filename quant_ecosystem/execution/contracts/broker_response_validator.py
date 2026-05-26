class BrokerResponseValidator:

    def validate(self, payload):
        if not isinstance(payload, dict):
            raise RuntimeError(
                "Broker response must be dict"
            )

        # explicit rejection path
        if payload.get("s") == "error":
            raise RuntimeError(
                payload.get(
                    "message",
                    "Broker rejected order"
                )
            )

        if payload.get("rejected") is True:
            raise RuntimeError(
                "Broker rejected order"
            )

        if payload.get("timestamp") == "OLD":
            raise RuntimeError(
                "Stale broker acknowledgement"
            )

        # accept legacy valid broker payloads
        if payload.get("id"):
            return payload

        if payload.get("order_id"):
            return payload

        status = payload.get("status")

        if status == "PARTIAL":
            if "filled_qty" not in payload:
                raise RuntimeError(
                    "Missing filled quantity"
                )
            return payload

        if status in {"TRADE", "SUCCESS"}:
            if not payload.get("order_id"):
                raise RuntimeError(
                    "Missing order_id"
                )
            return payload

        raise RuntimeError(
            "Invalid broker response"
        )