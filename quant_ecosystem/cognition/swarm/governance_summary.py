from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Tuple

from .governance_diagnostic import GovernanceDiagnostic
from .governance_insight import GovernanceInsight


@dataclass(frozen=True)
class GovernanceSummary:
    status: str
    selected_pattern_ids: Tuple[str, ...]
    insights: Tuple[GovernanceInsight, ...] = field(default_factory=tuple)
    diagnostics: Tuple[GovernanceDiagnostic, ...] = field(default_factory=tuple)
    observation_summary: Dict[str, Dict[str, int]] = field(default_factory=dict)
    schema_versions: Tuple[str, ...] = field(default_factory=tuple)
    provenance: Tuple[str, ...] = field(default_factory=tuple)
    source_keys: Tuple[str, ...] = field(default_factory=tuple)
    graph_node_count: int = 0
    relationship_count: int = 0
    dependency_count: int = 0
    replay_record_count: int = 0
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
