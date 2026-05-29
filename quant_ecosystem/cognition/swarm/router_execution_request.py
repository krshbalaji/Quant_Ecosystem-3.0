from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class RouterExecutionRequest:
    request_id: str
    route_type: str
    payload: Dict[str, Any]