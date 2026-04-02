"""Strategy DNA schema used by mutation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class StrategyDNA:
    """Portable representation of strategy logic and risk parameters."""

    entry_logic: str
    exit_logic: str
    stop_loss: float
    take_profit: float
    indicators: List[str] = field(default_factory=list)
    parameters: Dict[str, float] = field(default_factory=dict)
    timeframe: str = "5m"
    asset_class: str = "stocks"

    def to_dict(self) -> Dict:
        return {
            "entry_logic": self.entry_logic,
            "exit_logic": self.exit_logic,
            "stop_loss": float(self.stop_loss),
            "take_profit": float(self.take_profit),
            "indicators": list(self.indicators),
            "parameters": dict(self.parameters),
            "timeframe": self.timeframe,
            "asset_class": self.asset_class,
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "StrategyDNA":
        return cls(
            entry_logic=str(payload.get("entry_logic", "trend_follow_entry")),
            exit_logic=str(payload.get("exit_logic", "fixed_exit")),
            stop_loss=float(payload.get("stop_loss", 1.0)),
            take_profit=float(payload.get("take_profit", 2.0)),
            indicators=[str(item) for item in payload.get("indicators", ["ema", "rsi"])],
            parameters={str(k): float(v) for k, v in dict(payload.get("parameters", {})).items()},
            timeframe=str(payload.get("timeframe", "5m")),
            asset_class=str(payload.get("asset_class", "stocks")),
        )
