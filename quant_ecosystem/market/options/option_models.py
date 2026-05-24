from dataclasses import dataclass, field
from typing import Dict, List, Optional

from quant_ecosystem.market.options.greeks_models import (
    CanonicalGreeks,
)


@dataclass
class CanonicalOptionContract:
    symbol: str
    underlying: str
    strike: float
    expiry: str
    option_type: str

    bid: float = 0.0
    ask: float = 0.0
    ltp: float = 0.0
    volume: int = 0
    open_interest: int = 0
    implied_volatility: float = 0.0

    greeks: CanonicalGreeks = field(
        default_factory=CanonicalGreeks
    )

    metadata: Dict = field(default_factory=dict)

    @property
    def mid_price(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        return self.ltp


@dataclass
class CanonicalOptionChain:
    underlying: str
    expiry: str

    calls: List[CanonicalOptionContract] = field(
        default_factory=list
    )

    puts: List[CanonicalOptionContract] = field(
        default_factory=list
    )

    spot_price: float = 0.0
    timestamp: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def all_contracts(self):
        return self.calls + self.puts

    def strike_map(self):
        output = {}

        for contract in self.calls:
            output.setdefault(contract.strike, {})
            output[contract.strike]["CE"] = contract

        for contract in self.puts:
            output.setdefault(contract.strike, {})
            output[contract.strike]["PE"] = contract

        return output