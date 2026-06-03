from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class LearningPattern:
    pattern_id: str
    pattern_type: str
    classification_key: str
    frequency: int
    anomaly_count: int
    repeated_event_count: int
    source_key: Optional[str]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    schema_versions: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)
