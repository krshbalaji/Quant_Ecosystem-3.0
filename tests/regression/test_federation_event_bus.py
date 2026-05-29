from quant_ecosystem.cognition.swarm import (
    EventSubscription,
    FederationEvent,
    FederationEventBus,
)


def test_event_dispatch():

    bus = FederationEventBus()

    bus.subscribe(
        EventSubscription(
            subscriber_id="risk_engine",
            event_type="allocation",
        )
    )

    records = bus.publish(
        FederationEvent(
            event_id="E1",
            event_type="allocation",
            payload={},
        )
    )

    assert len(records) == 1