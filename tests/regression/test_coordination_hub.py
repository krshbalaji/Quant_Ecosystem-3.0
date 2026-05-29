from quant_ecosystem.cognition.swarm import (
    CoordinationHub,
    EventSubscription,
    FederationEvent,
    FederationEventBus,
)


def test_hub_coordinates():

    bus = FederationEventBus()

    bus.subscribe(
        EventSubscription(
            subscriber_id="router",
            event_type="execution",
        )
    )

    hub = CoordinationHub(bus)

    records = hub.coordinate(
        FederationEvent(
            event_id="E1",
            event_type="execution",
            payload={},
        )
    )

    assert len(records) == 1