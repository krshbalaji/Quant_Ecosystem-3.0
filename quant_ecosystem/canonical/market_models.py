"""
QE3 Canonical Market Models
Pack19 — Unified Data Canonicalization Layer
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_ecosystem.canonical.validators import (
    ensure_positive_number,
    ensure_string,
    normalize_timestamp,
    validate_asset_class,
    validate_market,
)


@dataclass
class CanonicalBase:
    provider: str
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.provider = ensure_string(
            self.provider,
            "provider",
        )


@dataclass
class CanonicalLTP(CanonicalBase):
    symbol: str = ""
    market: str = ""
    asset_class: str = "EQUITY"
    price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.symbol = ensure_string(self.symbol, "symbol")
        self.market = validate_market(self.market)
        self.asset_class = validate_asset_class(self.asset_class)

        self.price = ensure_positive_number(
            self.price,
            "price",
            allow_zero=False,
        )

        self.timestamp = normalize_timestamp(self.timestamp)


@dataclass
class CanonicalQuote(CanonicalBase):
    symbol: str = ""
    market: str = ""
    asset_class: str = "EQUITY"

    bid: float = 0.0
    ask: float = 0.0

    bid_size: int = 0
    ask_size: int = 0

    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    prev_close: float = 0.0

    volume: int = 0
    oi: int = 0

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.symbol = ensure_string(self.symbol, "symbol")
        self.market = validate_market(self.market)
        self.asset_class = validate_asset_class(self.asset_class)

        self.bid = ensure_positive_number(
            self.bid,
            "bid",
        )
        self.ask = ensure_positive_number(
            self.ask,
            "ask",
        )

        self.open = ensure_positive_number(
            self.open,
            "open",
        )
        self.high = ensure_positive_number(
            self.high,
            "high",
        )
        self.low = ensure_positive_number(
            self.low,
            "low",
        )
        self.close = ensure_positive_number(
            self.close,
            "close",
        )
        self.prev_close = ensure_positive_number(
            self.prev_close,
            "prev_close",
        )

        self.bid_size = int(self.bid_size)
        self.ask_size = int(self.ask_size)
        self.volume = int(self.volume)
        self.oi = int(self.oi)

        self.timestamp = normalize_timestamp(self.timestamp)


@dataclass
class CanonicalOHLCVBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    oi: int = 0

    def __post_init__(self):
        self.timestamp = normalize_timestamp(self.timestamp)

        self.open = ensure_positive_number(
            self.open,
            "open",
            allow_zero=False,
        )
        self.high = ensure_positive_number(
            self.high,
            "high",
            allow_zero=False,
        )
        self.low = ensure_positive_number(
            self.low,
            "low",
            allow_zero=False,
        )
        self.close = ensure_positive_number(
            self.close,
            "close",
            allow_zero=False,
        )

        self.volume = int(self.volume)
        self.oi = int(self.oi)


@dataclass
class CanonicalOHLCVSeries(CanonicalBase):
    symbol: str = ""
    market: str = ""
    asset_class: str = "EQUITY"
    interval: str = "1m"
    bars: List[CanonicalOHLCVBar] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()

        self.symbol = ensure_string(self.symbol, "symbol")
        self.market = validate_market(self.market)
        self.asset_class = validate_asset_class(self.asset_class)
        self.interval = ensure_string(
            self.interval,
            "interval",
        )

        normalized = []

        for bar in self.bars:
            if isinstance(bar, CanonicalOHLCVBar):
                normalized.append(bar)
            else:
                normalized.append(CanonicalOHLCVBar(**bar))

        self.bars = normalized


@dataclass
class CanonicalOrderBookLevel:
    price: float
    qty: int
    orders: int = 0

    def __post_init__(self):
        self.price = ensure_positive_number(
            self.price,
            "price",
        )

        self.qty = int(self.qty)
        self.orders = int(self.orders)


@dataclass
class CanonicalOrderBook(CanonicalBase):
    symbol: str = ""
    market: str = ""
    asset_class: str = "EQUITY"

    bids: List[CanonicalOrderBookLevel] = field(default_factory=list)
    asks: List[CanonicalOrderBookLevel] = field(default_factory=list)

    depth: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.symbol = ensure_string(self.symbol, "symbol")
        self.market = validate_market(self.market)
        self.asset_class = validate_asset_class(self.asset_class)

        normalized_bids = []
        normalized_asks = []

        for x in self.bids:
            if isinstance(x, CanonicalOrderBookLevel):
                normalized_bids.append(x)
            else:
                normalized_bids.append(CanonicalOrderBookLevel(**x))

        for x in self.asks:
            if isinstance(x, CanonicalOrderBookLevel):
                normalized_asks.append(x)
            else:
                normalized_asks.append(CanonicalOrderBookLevel(**x))

        self.bids = normalized_bids
        self.asks = normalized_asks

        self.depth = int(self.depth)
        self.timestamp = normalize_timestamp(self.timestamp)


@dataclass
class CanonicalOptionStrike:
    strike: float

    ltp: float = 0.0
    bid: float = 0.0
    ask: float = 0.0

    oi: int = 0
    volume: int = 0

    iv: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None

    def __post_init__(self):
        self.strike = ensure_positive_number(
            self.strike,
            "strike",
            allow_zero=False,
        )

        self.ltp = ensure_positive_number(
            self.ltp,
            "ltp",
        )
        self.bid = ensure_positive_number(
            self.bid,
            "bid",
        )
        self.ask = ensure_positive_number(
            self.ask,
            "ask",
        )

        self.oi = int(self.oi)
        self.volume = int(self.volume)


@dataclass
class CanonicalOptionChain(CanonicalBase):
    underlying: str = ""
    market: str = ""
    expiry: str = ""

    calls: List[CanonicalOptionStrike] = field(default_factory=list)
    puts: List[CanonicalOptionStrike] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.underlying = ensure_string(
            self.underlying,
            "underlying",
        )
        self.market = validate_market(self.market)
        self.expiry = ensure_string(
            self.expiry,
            "expiry",
        )

        normalized_calls = []
        normalized_puts = []

        for x in self.calls:
            if isinstance(x, CanonicalOptionStrike):
                normalized_calls.append(x)
            else:
                normalized_calls.append(CanonicalOptionStrike(**x))

        for x in self.puts:
            if isinstance(x, CanonicalOptionStrike):
                normalized_puts.append(x)
            else:
                normalized_puts.append(CanonicalOptionStrike(**x))

        self.calls = normalized_calls
        self.puts = normalized_puts

        self.timestamp = normalize_timestamp(self.timestamp)


@dataclass
class CanonicalFundamentals(CanonicalBase):
    symbol: str = ""

    market_cap: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    eps: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    dividend_yield: Optional[float] = None
    debt_equity: Optional[float] = None

    sector: Optional[str] = None
    industry: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.symbol = ensure_string(self.symbol, "symbol")


@dataclass
class CanonicalNewsItem(CanonicalBase):
    headline: str = ""
    summary: str = ""
    source: str = ""
    url: str = ""
    sentiment: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        super().__post_init__()

        self.headline = ensure_string(
            self.headline,
            "headline",
        )

        self.published_at = normalize_timestamp(
            self.published_at
        )