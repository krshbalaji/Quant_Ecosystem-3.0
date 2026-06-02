from datetime import datetime

from quant_ecosystem.cognition.swarm.execution_lineage import ExecutionLineage
from quant_ecosystem.cognition.swarm.audit_event import AuditEvent


def make_event(i: int) -> AuditEvent:
    return AuditEvent(
        event_id=f"e{i}",
        event_type="TEST",
        source_id="src",
        timestamp=datetime.utcnow(),
    )


def test_execution_lineage_shadow_parity():
    el = ExecutionLineage(lineage_id="LX")

    e1 = make_event(1)
    e2 = make_event(2)

    el.append(e1)
    el.append(e2)

    # legacy reads
    assert el.events == [e1, e2]
    assert el.count() == 2

    # shadow store parity
    shadow_get = el._shadow_store.get("LX")
    assert shadow_get == [e1, e2]
    assert el._shadow_store.latest("LX") == e2
