"""
QE3 Trade Accounting Models
Pack23
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List
import uuid


class AccountingMethod(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    WEIGHTED_AVG = "WEIGHTED_AVG"


@dataclass
class CanonicalTradeFill:
    broker: str
    symbol: str
    side: str
    qty: int
    price: float

    order_id: str = ""
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fees: float = 0.0
    slippage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.qty = int(self.qty)
        self.price = float(self.price)
        self.fees = float(self.fees)
        self.slippage = float(self.slippage)

        if self.qty <= 0:
            raise ValueError("qty must be > 0")

        if self.price < 0:
            raise ValueError("price cannot be negative")


@dataclass
class CanonicalTaxLot:
    symbol: str
    qty: int
    entry_price: float

    lot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    broker: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.qty = int(self.qty)
        self.entry_price = float(self.entry_price)

        if self.qty <= 0:
            raise ValueError("lot qty must be > 0")


@dataclass
class CanonicalAccountingSnapshot:
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    total_fees: float = 0.0
    total_slippage: float = 0.0

    open_lots: List[CanonicalTaxLot] = field(default_factory=list)
    fills_processed: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.realized_pnl = float(self.realized_pnl)
        self.unrealized_pnl = float(self.unrealized_pnl)
        self.gross_pnl = float(self.gross_pnl)
        self.net_pnl = float(self.net_pnl)
        self.total_fees = float(self.total_fees)
        self.total_slippage = float(self.total_slippage)
        self.fills_processed = int(self.fills_processed)