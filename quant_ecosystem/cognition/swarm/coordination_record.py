from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CoordinationRecord:
    proposal_id: str
    outcome: str
    confidence: float
    participant_count: int
    created_at: datetime = datetime.utcnow()