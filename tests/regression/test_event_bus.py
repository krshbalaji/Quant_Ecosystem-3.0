import pytest

from quant_ecosystem.core.event_bus import EventBus


def test_subscribe_and_publish_receives_event():
    bus = EventBus()
    received = []

    def cb(evt):
        received.append(evt)

    bus.subscribe("topicA", cb)
    bus.publish("topicA", "payload")

    assert received == ["payload"]


def test_multiple_subscribers_receive_in_order():
    bus = EventBus()
    seq = []

    def a(evt):
        seq.append(("a", evt))

    def b(evt):
        seq.append(("b", evt))

    bus.subscribe("t", a)
    bus.subscribe("t", b)
    bus.publish("t", 123)

    assert seq == [("a", 123), ("b", 123)]


def test_unsubscribe_stops_receiving():
    bus = EventBus()
    received = []

    def cb(evt):
        received.append(evt)

    bus.subscribe("x", cb)
    bus.unsubscribe("x", cb)
    bus.publish("x", "nope")

    assert received == []


def test_publish_without_subscribers_no_exception():
    bus = EventBus()

    # Should not raise
    bus.publish("missing_topic", {"ok": True})
