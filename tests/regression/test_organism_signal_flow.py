from quant_ecosystem.core.event_bus import EventBus
from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.core.memory_event_adapter import MemoryEventAdapter


def test_organism_eventbus_to_memory_adapter_flow():
    # Setup foundations
    bus = EventBus()
    store = MultiMapStore()
    adapter = MemoryEventAdapter(store)

    # local receiver to assert delivery
    received = []

    def recorder(ev):
        received.append(ev)

    # Subscribe adapter and recorder to the execution outcome topic
    topic = "execution.outcome"
    bus.subscribe(topic, adapter.handle_event)
    bus.subscribe(topic, recorder)

    # Publish a sample execution outcome event
    event = {"event_type": topic, "payload": {"order_id": "ord-123", "status": "filled"}}
    bus.publish(topic, event)

    # Assertions
    # event received by recorder
    assert len(received) == 1
    assert received[0] is event

    # event stored in MultiMapStore under the event_type key
    stored = store.get(topic)
    assert stored == [event]
    assert store.latest(topic) == event
