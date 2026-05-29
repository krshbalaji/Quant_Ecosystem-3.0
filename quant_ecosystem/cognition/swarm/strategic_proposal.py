from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class StrategicProposal:
    proposal_id: str
    domain: str
    title: str
    payload: Dict[str, Any]