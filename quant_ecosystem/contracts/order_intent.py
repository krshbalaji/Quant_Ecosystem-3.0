from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import _profile_value


@dataclass
class OrderIntent:
    symbol: str
    side: str
    qty: int
    order_type: str = "MARKET"
    profile: ProfileTypes | str = ProfileTypes.INTRADAY
    reason: str = ""
    approval_id: Optional[str] = None
    source: str = "UNKNOWN"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": str(self.side).upper(),
            "qty": int(self.qty),
            "order_type": str(self.order_type).upper(),
            "profile": _profile_value(self.profile),
            "reason": self.reason,
            "approval_id": self.approval_id,
            "source": self.source,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "OrderIntent":
        return cls(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "")).upper(),
            qty=int(data.get("qty", 0) or 0),
            order_type=str(data.get("order_type", "MARKET")).upper(),
            profile=data.get("profile", ProfileTypes.INTRADAY),
            reason=str(data.get("reason", "")),
            approval_id=data.get("approval_id"),
            source=str(data.get("source", "UNKNOWN")),
            metadata=dict(data.get("metadata") or {}),
        )
