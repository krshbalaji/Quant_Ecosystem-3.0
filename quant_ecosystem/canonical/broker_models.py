"""
QE3 Canonical Broker Models
Pack19 — Unified Data Canonicalization Layer
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from quant_ecosystem.canonical.validators import (
    ensure_positive_number,
    ensure_string,
    normalize_timestamp,
    validate_order_status,
    validate_side,
)


@dataclass
class CanonicalBrokerBase:
    provider: str
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.provider = ensure_string(
            self.provider,
            "provider",
        )


@dataclass
class CanonicalBalance(CanonicalBrokerBase):
    cash: float = 0.0
    margin_available: float = 0.0
    margin_used: float = 0.0
    collateral: float = 0.0
    currency: str = "INR"

    def __post_init__(self):
        super().__post_init__()

        self.cash = ensure_positive_number(
            self.cash,
            "cash",
        )
        self.margin_available = ensure_positive_number(
            self.margin_available,
            "margin_available",
        )
        self.margin_used = ensure_positive_number(
            self.margin_used,
            "margin_used",
        )
        self.collateral = ensure_positive_number(
            self.collateral,
            "collateral",
        )

        self.currency = ensure_string(
            self.currency,
            "currency",
        )


@dataclass
class CanonicalPosition(CanonicalBrokerBase):
    symbol: str = ""
    qty: int = 0
    avg_price: float = 0.0
    ltp: float = 0.0

    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    side: str = "BUY"
    product_type: str = "CNC"

    def __post_init__(self):
        super().__post_init__()

        self.symbol = ensure_string(
            self.symbol,
            "symbol",
        )

        self.qty = int(self.qty)

        self.avg_price = ensure_positive_number(
            self.avg_price,
            "avg_price",
        )

        self.ltp = ensure_positive_number(
            self.ltp,
            "ltp",
        )

        self.side = validate_side(self.side)

        self.product_type = ensure_string(
            self.product_type,
            "product_type",
        )


@dataclass
class CanonicalOrder(CanonicalBrokerBase):
    order_id: str = ""
    symbol: str = ""

    side: str = "BUY"

    qty: int = 0
    filled_qty: int = 0
    remaining_qty: int = 0

    avg_price: float = 0.0

    status: str = "PENDING"

    order_type: str = "MARKET"
    product: str = "CNC"

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.order_id = ensure_string(
            self.order_id,
            "order_id",
        )

        self.symbol = ensure_string(
            self.symbol,
            "symbol",
        )

        self.side = validate_side(self.side)
        self.status = validate_order_status(self.status)

        self.qty = int(self.qty)
        self.filled_qty = int(self.filled_qty)
        self.remaining_qty = int(self.remaining_qty)

        self.avg_price = ensure_positive_number(
            self.avg_price,
            "avg_price",
        )

        self.order_type = ensure_string(
            self.order_type,
            "order_type",
        )

        self.product = ensure_string(
            self.product,
            "product",
        )

        self.timestamp = normalize_timestamp(
            self.timestamp
        )


@dataclass
class CanonicalExecution(CanonicalBrokerBase):
    execution_id: str = ""
    order_id: str = ""
    symbol: str = ""

    qty: int = 0
    price: float = 0.0

    fees: float = 0.0

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.execution_id = ensure_string(
            self.execution_id,
            "execution_id",
        )

        self.order_id = ensure_string(
            self.order_id,
            "order_id",
        )

        self.symbol = ensure_string(
            self.symbol,
            "symbol",
        )

        self.qty = int(self.qty)

        self.price = ensure_positive_number(
            self.price,
            "price",
        )

        self.fees = ensure_positive_number(
            self.fees,
            "fees",
        )

        self.timestamp = normalize_timestamp(
            self.timestamp
        )