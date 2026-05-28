from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime


@dataclass
class SwarmMessage:
    sender_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 1