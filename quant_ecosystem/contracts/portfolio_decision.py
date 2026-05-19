from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import _profile_value


@dataclass
class PortfolioDecision:
    action: str
    symbol: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    profile: ProfileTypes | str = ProfileTypes.INVESTMENT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": str(self.action).upper(),
            "symbol": self.symbol,
            "confidence": float(self.confidence),
            "reason": self.reason,
            "profile": _profile_value(self.profile),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PortfolioDecision":
        return cls(
            action=str(data.get("action", "")).upper(),
            symbol=data.get("symbol"),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            reason=str(data.get("reason", "")),
            profile=data.get("profile", ProfileTypes.INVESTMENT),
            metadata=dict(data.get("metadata") or {}),
        )
