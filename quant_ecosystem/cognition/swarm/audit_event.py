from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: str
    source_id: str
    timestamp: datetime