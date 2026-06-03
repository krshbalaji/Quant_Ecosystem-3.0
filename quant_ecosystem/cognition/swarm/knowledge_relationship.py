from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class KnowledgeRelationship:
    source_id: str
    target_id: str
    relationship_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
