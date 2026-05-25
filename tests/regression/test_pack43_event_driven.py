from quant_ecosystem.events import (
    DomainEvent,
    subscriber_registry,
    event_bus,
)


def setup_function():
    subscriber_registry.clear()


def test_subscribe():
    def handler(event):
        return "OK"

    subscriber_registry.subscribe(
        "ORDER_CREATED",
        handler,
    )

    assert len(
        subscriber_registry.handlers(
            "ORDER_CREATED"
        )
    ) == 1


def test_publish_single():
    def handler(event):
        return event.payload["id"]

    subscriber_registry.subscribe(
        "ORDER_CREATED",
        handler,
    )

    event = DomainEvent(
        name="ORDER_CREATED",
        payload={"id": 101},
    )

    result = event_bus.publish(
        event
    )

    assert result == [101]


def test_publish_multiple():
    def h1(event):
        return 1

    def h2(event):
        return 2

    subscriber_registry.subscribe(
        "PING",
        h1,
    )

    subscriber_registry.subscribe(
        "PING",
        h2,
    )

    event = DomainEvent(
        name="PING",
        payload={},
    )

    result = event_bus.publish(
        event
    )

    assert result == [1, 2]


def test_no_subscribers():
    event = DomainEvent(
        name="NONE",
        payload={},
    )

    result = event_bus.publish(
        event
    )

    assert result == []


def test_event_metadata():
    event = DomainEvent(
        name="TEST",
        payload={"x": 1},
        metadata={"source": "qe3"},
    )

    assert (
        event.metadata["source"]
        == "qe3"
    )