from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KnowledgeDependency:
    dependent_id: str
    dependency_id: str
    dependency_type: str
    strength: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
