from quant_ecosystem.core.event_bus import EventBus
from quant_ecosystem.core.execution_outcome_publisher import ExecutionOutcomePublisher


def test_publish_outcome_emits_event():
    bus = EventBus()
    rec = []

    def cb(evt):
        rec.append(evt)

    bus.subscribe("execution.outcome", cb)
    p = ExecutionOutcomePublisher(bus)
    outcome = {"id": "ex1", "status": "ok"}
    p.publish_outcome(outcome)

    assert rec == [outcome]
