from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass(frozen=True)
class FederationMemorySnapshot:
    organism_id: str
    memory_type: str
    payload: Dict[str, Any]
    lineage_id: str
    constitutional_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)