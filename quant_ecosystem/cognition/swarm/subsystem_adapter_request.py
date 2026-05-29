from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class SubsystemAdapterRequest:
    request_id: str
    subsystem_name: str
    payload: Dict[str, Any]