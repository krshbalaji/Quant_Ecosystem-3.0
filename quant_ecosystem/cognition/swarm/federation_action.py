from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class FederationAction:
    action_id: str
    action_type: str
    payload: Dict[str, Any]