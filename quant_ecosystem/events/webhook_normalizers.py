"""
QE3 Broker Event Normalizers
Pack24
"""

from quant_ecosystem.events.broker_event_models import (
    CanonicalBrokerEvent,
    CanonicalBrokerEventType,
    BrokerEventSource,
)


EVENT_MAP = {
    "ACK": CanonicalBrokerEventType.ORDER_ACK,
    "OPEN": CanonicalBrokerEventType.ORDER_ACK,
    "PARTIAL": CanonicalBrokerEventType.PARTIAL_FILL,
    "PARTIALLY_FILLED": CanonicalBrokerEventType.PARTIAL_FILL,
    "FILLED": CanonicalBrokerEventType.FULL_FILL,
    "CANCELLED": CanonicalBrokerEventType.CANCELLED,
    "REJECTED": CanonicalBrokerEventType.REJECTED,
    "MODIFIED": CanonicalBrokerEventType.MODIFIED,
    "ERROR": CanonicalBrokerEventType.ERROR,
}


class BaseWebhookNormalizer:
    broker = "unknown"

    def normalize_event_type(self, raw_status):
        key = str(raw_status).strip().upper()

        if key not in EVENT_MAP:
            raise ValueError(f"unsupported event status: {raw_status}")

        return EVENT_MAP[key]

    def normalize(self, payload, source=BrokerEventSource.WEBHOOK):
        raise NotImplementedError


class FyersWebhookNormalizer(BaseWebhookNormalizer):
    broker = "fyers"

    def normalize(self, payload, source=BrokerEventSource.WEBHOOK):
        return CanonicalBrokerEvent(
            broker=self.broker,
            event_type=self.normalize_event_type(
                payload.get("status", "ERROR")
            ),
            source=source,
            symbol=payload.get("symbol", ""),
            order_id=payload.get("order_id", ""),
            broker_order_id=payload.get("broker_order_id", ""),
            qty=payload.get("filled_qty", 0),
            price=payload.get("avg_fill_price", 0.0),
            payload=payload,
        )


class GrowwWebhookNormalizer(BaseWebhookNormalizer):
    broker = "groww"

    def normalize(self, payload, source=BrokerEventSource.WEBHOOK):
        return CanonicalBrokerEvent(
            broker=self.broker,
            event_type=self.normalize_event_type(
                payload.get("status", "ERROR")
            ),
            source=source,
            symbol=payload.get("instrument", ""),
            order_id=payload.get("order_id", ""),
            broker_order_id=payload.get("broker_order_id", ""),
            qty=payload.get("filled_qty", 0),
            price=payload.get("avg_fill_price", 0.0),
            payload=payload,
        )


class ViewTradeWebhookNormalizer(BaseWebhookNormalizer):
    broker = "viewtrade"

    def normalize(self, payload, source=BrokerEventSource.WEBHOOK):
        return CanonicalBrokerEvent(
            broker=self.broker,
            event_type=self.normalize_event_type(
                payload.get("status", "ERROR")
            ),
            source=source,
            symbol=payload.get("ticker", ""),
            order_id=payload.get("order_id", ""),
            broker_order_id=payload.get("broker_order_id", ""),
            qty=payload.get("filled_qty", 0),
            price=payload.get("avg_fill_price", 0.0),
            payload=payload,
        )


class CoinSwitchWebhookNormalizer(BaseWebhookNormalizer):
    broker = "coinswitch"

    def normalize(self, payload, source=BrokerEventSource.WEBHOOK):
        return CanonicalBrokerEvent(
            broker=self.broker,
            event_type=self.normalize_event_type(
                payload.get("status", "ERROR")
            ),
            source=source,
            symbol=payload.get("symbol", ""),
            order_id=payload.get("order_id", ""),
            broker_order_id=payload.get("broker_order_id", ""),
            qty=payload.get("filled_qty", 0),
            price=payload.get("avg_fill_price", 0.0),
            payload=payload,
        )