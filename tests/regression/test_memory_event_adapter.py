from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.core.memory_event_adapter import MemoryEventAdapter


def test_memory_event_adapter_stores_event_by_type_name():
    store = MultiMapStore()
    adapter = MemoryEventAdapter(store)

    event = {"event_type": "TestEvent", "value": 42}
    adapter.handle_event(event)

    assert store.get("TestEvent") == [event]

    class Custom:
        pass

    c = Custom()
    adapter.handle_event(c)
    assert store.get("Custom") == [c]
