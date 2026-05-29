from dataclasses import dataclass, field
from typing import List

from .audit_event import AuditEvent


@dataclass
class ExecutionLineage:
    lineage_id: str
    events: List[AuditEvent] = field(default_factory=list)

    def append(
        self,
        event: AuditEvent,
    ) -> None:
        self.events.append(event)

    def count(self) -> int:
        return len(self.events)