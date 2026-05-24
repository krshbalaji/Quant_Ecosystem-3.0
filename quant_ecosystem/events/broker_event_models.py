"""
QE3 Broker Event Models
Pack24
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any
import uuid


class CanonicalBrokerEventType(str, Enum):
    ORDER_ACK = "ORDER_ACK"
    PARTIAL_FILL = "PARTIAL_FILL"
    FULL_FILL = "FULL_FILL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    ERROR = "ERROR"
    HEARTBEAT = "HEARTBEAT"
    DISCONNECT = "DISCONNECT"
    RECONNECT = "RECONNECT"


class BrokerEventSource(str, Enum):
    WEBHOOK = "WEBHOOK"
    WEBSOCKET = "WEBSOCKET"
    POLLING = "POLLING"
    INTERNAL = "INTERNAL"


@dataclass
class CanonicalBrokerEvent:
    broker: str
    event_type: CanonicalBrokerEventType
    source: BrokerEventSource

    symbol: str = ""
    order_id: str = ""
    broker_order_id: str = ""
    qty: int = 0
    price: float = 0.0

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.qty = int(self.qty)
        self.price = float(self.price)