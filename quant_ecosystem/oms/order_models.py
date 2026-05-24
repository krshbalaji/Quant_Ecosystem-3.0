"""
QE3 OMS canonical order lifecycle models
Pack22
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import uuid


class CanonicalOrderStatus(str, Enum):
    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class CanonicalEventType(str, Enum):
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACK = "ORDER_ACK"
    PARTIAL_FILL = "PARTIAL_FILL"
    FULL_FILL = "FULL_FILL"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


@dataclass
class CanonicalExecutionEvent:
    order_id: str
    event_type: CanonicalEventType
    qty: int = 0
    price: float = 0.0
    broker: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CanonicalOrderLifecycle:
    broker: str
    symbol: str
    side: str
    qty: int

    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filled_qty: int = 0
    avg_fill_price: float = 0.0
    status: CanonicalOrderStatus = CanonicalOrderStatus.NEW
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def remaining_qty(self):
        return max(self.qty - self.filled_qty, 0)

    def is_terminal(self):
        return self.status in {
            CanonicalOrderStatus.FILLED,
            CanonicalOrderStatus.CANCELLED,
            CanonicalOrderStatus.REJECTED,
            CanonicalOrderStatus.FAILED,
            CanonicalOrderStatus.EXPIRED,
        }