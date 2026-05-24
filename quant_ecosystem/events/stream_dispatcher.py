"""
QE3 Stream Dispatcher
Pack24
"""

from quant_ecosystem.events import (
    event_ingestion_engine,
    CanonicalBrokerEvent,
    CanonicalBrokerEventType,
    BrokerEventSource,
)


class StreamDispatcher:
    """
    Websocket / stream style event ingestion
    """

    def dispatch(self, broker_event):
        return event_ingestion_engine.ingest(
            broker_event
        )

    def heartbeat(self, broker: str):
        evt = CanonicalBrokerEvent(
            broker=broker,
            event_type=CanonicalBrokerEventType.HEARTBEAT,
            source=BrokerEventSource.WEBSOCKET,
        )

        return self.dispatch(evt)

    def disconnect(self, broker: str):
        evt = CanonicalBrokerEvent(
            broker=broker,
            event_type=CanonicalBrokerEventType.DISCONNECT,
            source=BrokerEventSource.WEBSOCKET,
        )

        return self.dispatch(evt)

    def reconnect(self, broker: str):
        evt = CanonicalBrokerEvent(
            broker=broker,
            event_type=CanonicalBrokerEventType.RECONNECT,
            source=BrokerEventSource.WEBSOCKET,
        )

        return self.dispatch(evt)


stream_dispatcher = StreamDispatcher()