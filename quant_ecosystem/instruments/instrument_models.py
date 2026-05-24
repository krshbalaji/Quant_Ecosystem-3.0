"""
QE3 Instrument Models
Pack25
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"
    ETF = "ETF"
    INDEX = "INDEX"


class InstrumentType(str, Enum):
    SPOT = "SPOT"
    DERIVATIVE = "DERIVATIVE"


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


@dataclass
class CanonicalInstrument:
    symbol: str
    asset_class: AssetClass
    instrument_type: InstrumentType

    exchange: str = ""
    underlying: str = ""

    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[OptionType] = None

    lot_size: int = 1
    tick_size: float = 0.01
    contract_multiplier: float = 1.0

    currency: str = "INR"

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_option(self):
        return self.asset_class == AssetClass.OPTION

    def is_future(self):
        return self.asset_class == AssetClass.FUTURE

    def is_equity(self):
        return self.asset_class == AssetClass.EQUITY

    def is_crypto(self):
        return self.asset_class == AssetClass.CRYPTO

    def is_forex(self):
        return self.asset_class == AssetClass.FOREX

    def is_derivative(self):
        return (
            self.instrument_type
            == InstrumentType.DERIVATIVE
        )