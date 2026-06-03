from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class GovernanceObservation:
    observation_id: str
    timestamp: datetime
    pattern_id: Optional[str]
    category: Optional[str]
    source_keys: Tuple[str, ...] = field(default_factory=tuple)
    lineage_ids: Tuple[str, ...] = field(default_factory=tuple)
    status: str = "OK"
    summary: Optional[str] = None
    issues: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)
