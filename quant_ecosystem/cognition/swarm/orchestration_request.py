from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class OrchestrationRequest:
    request_id: str
    workflow_type: str
    payload: Dict[str, Any]