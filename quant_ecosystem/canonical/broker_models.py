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

from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class ProductType(str, Enum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"
    DELIVERY = "DELIVERY"


@dataclass
class CanonicalOrderRequest:
    provider: str
    symbol: str
    side: str
    qty: int

    order_type: str = "MARKET"
    product: str = "CNC"
    price: float = 0.0

    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.provider = ensure_string(self.provider, "provider")
        self.symbol = ensure_string(self.symbol, "symbol")
        self.side = validate_side(self.side)
        self.qty = int(self.qty)

        if self.qty <= 0:
            raise ValueError("qty must be > 0")

        self.order_type = ensure_string(
            self.order_type,
            "order_type",
        )

        self.product = ensure_string(
            self.product,
            "product",
        )

        self.price = float(self.price)


@dataclass
class CanonicalModifyRequest:
    provider: str
    order_id: str
    qty: int
    price: float = 0.0

    def __post_init__(self):
        self.provider = ensure_string(self.provider, "provider")
        self.order_id = ensure_string(self.order_id, "order_id")
        self.qty = int(self.qty)
        self.price = float(self.price)


@dataclass
class CanonicalCancelRequest:
    provider: str
    order_id: str

    def __post_init__(self):
        self.provider = ensure_string(self.provider, "provider")
        self.order_id = ensure_string(self.order_id, "order_id")

@dataclass
class CanonicalMarginSnapshot(CanonicalBrokerBase):
    available: float = 0.0
    used: float = 0.0
    collateral: float = 0.0
    leverage: float = 1.0

    def __post_init__(self):
        super().__post_init__()

        self.available = float(self.available)
        self.used = float(self.used)
        self.collateral = float(self.collateral)
        self.leverage = float(self.leverage)

        if self.available < 0:
            raise ValueError("available margin cannot be negative")

        if self.used < 0:
            raise ValueError("used margin cannot be negative")

        if self.collateral < 0:
            raise ValueError("collateral cannot be negative")

        if self.leverage <= 0:
            raise ValueError("leverage must be > 0")


@dataclass
class CanonicalExposureSnapshot(CanonicalBrokerBase):
    portfolio_exposure_pct: float = 0.0
    symbol_exposure_pct: Dict[str, float] = field(default_factory=dict)
    sector_exposure_pct: Dict[str, float] = field(default_factory=dict)
    asset_class_exposure_pct: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()

        self.portfolio_exposure_pct = float(self.portfolio_exposure_pct)
        self.symbol_exposure_pct = dict(self.symbol_exposure_pct)
        self.sector_exposure_pct = dict(self.sector_exposure_pct)
        self.asset_class_exposure_pct = dict(self.asset_class_exposure_pct)


@dataclass
class CanonicalRiskSnapshot(CanonicalBrokerBase):
    daily_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    margin_utilization_pct: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    def __post_init__(self):
        super().__post_init__()

        self.daily_loss_pct = float(self.daily_loss_pct)
        self.drawdown_pct = float(self.drawdown_pct)
        self.margin_utilization_pct = float(self.margin_utilization_pct)
        self.realized_pnl = float(self.realized_pnl)
        self.unrealized_pnl = float(self.unrealized_pnl)


@dataclass
class CanonicalPortfolioSnapshot(CanonicalBrokerBase):
    positions: list = field(default_factory=list)
    balance: Optional[CanonicalBalance] = None
    margin: Optional[CanonicalMarginSnapshot] = None
    exposure: Optional[CanonicalExposureSnapshot] = None
    risk: Optional[CanonicalRiskSnapshot] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.positions = list(self.positions)

        if self.balance is not None and not isinstance(
            self.balance,
            CanonicalBalance,
        ):
            raise ValueError("balance must be CanonicalBalance")

        if self.margin is not None and not isinstance(
            self.margin,
            CanonicalMarginSnapshot,
        ):
            raise ValueError("margin must be CanonicalMarginSnapshot")

        if self.exposure is not None and not isinstance(
            self.exposure,
            CanonicalExposureSnapshot,
        ):
            raise ValueError("exposure must be CanonicalExposureSnapshot")

        if self.risk is not None and not isinstance(
            self.risk,
            CanonicalRiskSnapshot,
        ):
            raise ValueError("risk must be CanonicalRiskSnapshot")

        self.timestamp = normalize_timestamp(self.timestamp)                