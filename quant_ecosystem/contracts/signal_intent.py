from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

from quant_ecosystem.contracts.profile_types import ProfileTypes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile_value(value: ProfileTypes | str) -> str:
    return value.value if isinstance(value, ProfileTypes) else str(value).upper()


@dataclass
class SignalIntent:
    symbol: str
    side: str
    profile: ProfileTypes | str
    strategy: str
    confidence: float = 0.0
    horizon: str = "UNKNOWN"
    source: str = "UNKNOWN"
    timestamp: str = field(default_factory=_utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": str(self.side).upper(),
            "profile": _profile_value(self.profile),
            "strategy": self.strategy,
            "confidence": float(self.confidence),
            "horizon": self.horizon,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SignalIntent":
        return cls(
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "")).upper(),
            profile=data.get("profile", ProfileTypes.INTRADAY),
            strategy=str(data.get("strategy", "")),
            confidence=float(data.get("confidence", 0.0) or 0.0),
            horizon=str(data.get("horizon", "UNKNOWN")),
            source=str(data.get("source", "UNKNOWN")),
            timestamp=str(data.get("timestamp") or _utc_now()),
            metadata=dict(data.get("metadata") or {}),
        )
