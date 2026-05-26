class BrokerFaultSimulator:

    @staticmethod
    def false_success():
        return {
            "status": "SUCCESS",
            "order_id": None,
        }

    @staticmethod
    def malformed_success():
        return {
            "ok": True
        }

    @staticmethod
    def partial_fill_missing_qty():
        return {
            "status": "PARTIAL"
        }

    @staticmethod
    def duplicate_ack():
        return {
            "status": "TRADE",
            "order_id": "DUPLICATE-ACK-001",
        }

    @staticmethod
    def stale_ack():
        return {
            "status": "TRADE",
            "order_id": "STALE-ACK-OLD",
            "timestamp": "OLD",
        }

    @staticmethod
    def reject_with_success_flag():
        return {
            "status": "SUCCESS",
            "rejected": True,
            "reason": "Margin insufficient",
        }