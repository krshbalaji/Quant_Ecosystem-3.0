from .audit_event import AuditEvent
from .execution_lineage import ExecutionLineage


class ExecutionTraceEngine:

    def record(
        self,
        lineage: ExecutionLineage,
        event: AuditEvent,
    ) -> None:

        lineage.append(event)

    def event_count(
        self,
        lineage: ExecutionLineage,
    ) -> int:

        return lineage.count()