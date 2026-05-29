from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class FederationObservation:
    organism_id: str
    category: str
    observation_id: str
    payload: Dict[str, Any]