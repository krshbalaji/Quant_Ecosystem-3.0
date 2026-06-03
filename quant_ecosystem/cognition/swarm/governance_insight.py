from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class GovernanceInsight:
    insight_id: str
    category: str
    summary: str
    severity: str = "INFO"
    source_pattern_ids: Tuple[str, ...] = field(default_factory=tuple)
    source_keys: Tuple[str, ...] = field(default_factory=tuple)
    provenance: Tuple[str, ...] = field(default_factory=tuple)
    explanation: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
