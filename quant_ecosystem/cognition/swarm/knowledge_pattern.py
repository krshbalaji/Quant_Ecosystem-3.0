from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Tuple


@dataclass(frozen=True)
class KnowledgePattern:
    category: str
    frequency: int
    pattern_id: Optional[str] = None
    pattern_type: Optional[str] = None
    source_keys: Tuple[str, ...] = field(default_factory=tuple)
    aggregated_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    schema_versions: Tuple[str, ...] = field(default_factory=tuple)
    provenance: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)