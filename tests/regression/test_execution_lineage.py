from datetime import datetime

from quant_ecosystem.cognition.swarm import (
    AuditEvent,
    ExecutionLineage,
)


def test_lineage_records_events():

    lineage = ExecutionLineage(
        lineage_id="LINEAGE-1"
    )

    lineage.append(
        AuditEvent(
            event_id="E1",
            event_type="authorization",
            source_id="alpha",
            timestamp=datetime.utcnow(),
        )
    )

    assert lineage.count() == 1