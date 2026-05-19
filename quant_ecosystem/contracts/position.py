from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import _profile_value


@dataclass
class Position:
    symbol: str
    qty: int
    avg_entry: float
    profile: ProfileTypes | str = ProfileTypes.INTRADAY
    strategy: str = ""
    thesis: Dict[str, Any] = field(default_factory=dict)
    lifecycle: str = "OPEN"
    pnl_realized: float = 0.0
    pnl_unrealized: float = 0.0
    source: str = "UNKNOWN"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": int(self.qty),
            "avg_entry": float(self.avg_entry),
            "profile": _profile_value(self.profile),
            "strategy": self.strategy,
            "thesis": dict(self.thesis or {}),
            "lifecycle": str(self.lifecycle).upper(),
            "pnl_realized": float(self.pnl_realized),
            "pnl_unrealized": float(self.pnl_unrealized),
            "source": self.source,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Position":
        return cls(
            symbol=str(data.get("symbol", "")),
            qty=int(data.get("qty", 0) or 0),
            avg_entry=float(data.get("avg_entry", 0.0) or 0.0),
            profile=data.get("profile", ProfileTypes.INTRADAY),
            strategy=str(data.get("strategy", "")),
            thesis=dict(data.get("thesis") or {}),
            lifecycle=str(data.get("lifecycle", "OPEN")).upper(),
            pnl_realized=float(data.get("pnl_realized", 0.0) or 0.0),
            pnl_unrealized=float(data.get("pnl_unrealized", 0.0) or 0.0),
            source=str(data.get("source", "UNKNOWN")),
            metadata=dict(data.get("metadata") or {}),
        )
