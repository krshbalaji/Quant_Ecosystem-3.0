from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class FederationEvent:
    event_id: str
    event_type: str
    payload: Dict[str, Any]