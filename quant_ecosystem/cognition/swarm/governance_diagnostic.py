from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class GovernanceDiagnostic:
    diagnostic_id: str
    status: str
    source: str
    issues: Tuple[str, ...] = field(default_factory=tuple)
    details: Dict[str, Any] = field(default_factory=dict)
