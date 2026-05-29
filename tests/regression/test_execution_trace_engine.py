from datetime import datetime

from quant_ecosystem.cognition.swarm import (
    AuditEvent,
    ExecutionLineage,
    ExecutionTraceEngine,
)


def test_trace_engine_records():

    lineage = ExecutionLineage(
        lineage_id="TRACE-1"
    )

    engine = ExecutionTraceEngine()

    engine.record(
        lineage,
        AuditEvent(
            event_id="E1",
            event_type="execution",
            source_id="alpha",
            timestamp=datetime.utcnow(),
        ),
    )

    assert engine.event_count(lineage) == 1