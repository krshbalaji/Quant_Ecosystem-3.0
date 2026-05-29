from quant_ecosystem.cognition.swarm import (
    EventDispatchRecord,
)


def test_dispatch_record():

    record = EventDispatchRecord(
        event_id="E1",
        subscriber_id="router",
        dispatched=True,
    )

    assert record.dispatched