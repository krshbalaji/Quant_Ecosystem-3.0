"""Institutional strategy registry for Strategy Bank Engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class StrategyMetadata:
    """Normalized metadata tracked for each strategy."""

    id: str
    asset_class: str = "stocks"
    timeframe: str = "5m"
    category: str = "momentum"
    regime_preference: List[str] = None
    sharpe: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    expectancy: float = 0.0
    active: bool = False
    allocation_pct: float = 0.0
    correlation_cluster: str = ""
    stage: str = "CANDIDATE"
    score: float = 0.0
    sample_size: int = 0
    returns: List[float] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "asset_class": self.asset_class,
            "timeframe": self.timeframe,
            "category": self.category,
            "regime_preference": list(self.regime_preference or []),
            "sharpe": float(self.sharpe),
            "profit_factor": float(self.profit_factor),
            "max_drawdown": float(self.max_drawdown),
            "win_rate": float(self.win_rate),
            "expectancy": float(self.expectancy),
            "active": bool(self.active),
            "allocation_pct": float(self.allocation_pct),
            "correlation_cluster": self.correlation_cluster,
            "stage": self.stage,
            "score": float(self.score),
            "sample_size": int(self.sample_size),
            "returns": list(self.returns or []),
        }


class StrategyRegistryStore:
    """Persistent metadata store for strategy lifecycle and allocation decisions."""

    def __init__(self, metadata_path: str = "strategy_bank/metadata/strategy_registry.json", **kwargs):
        self.metadata_file = Path(metadata_path)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self._items: Dict[str, Dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.metadata_file.exists():
            self._items = {}
            return
        try:
            self._items = json.loads(self.metadata_file.read_text(encoding="utf-8"))
        except Exception:
            self._items = {}

    def save(self) -> None:
        self.metadata_file.write_text(json.dumps(self._items, indent=2), encoding="utf-8")

    def get(self, strategy_id: str) -> Optional[Dict]:
        return self._items.get(strategy_id)

    def all(self) -> List[Dict]:
        return [self._items[key] for key in sorted(self._items.keys())]

    def upsert(self, payload: Dict) -> Dict:
        strategy_id = str(payload.get("id", "")).strip()
        if not strategy_id:
            raise ValueError("strategy metadata requires non-empty id")
        current = self._items.get(strategy_id, {})
        merged = {**current, **payload}
        merged["id"] = strategy_id
        self._items[strategy_id] = merged
        return merged

    def bulk_upsert(self, rows: Iterable[Dict]) -> None:
        for row in rows:
            self.upsert(row)
        self.save()

    def update_metrics(self, strategy_id: str, metrics: Dict) -> Dict:
        current = self._items.get(strategy_id)
        if not current:
            current = self.upsert({"id": strategy_id})
        current.update(
            {
                "sharpe": float(metrics.get("sharpe", current.get("sharpe", 0.0))),
                "profit_factor": float(metrics.get("profit_factor", current.get("profit_factor", 0.0))),
                "max_drawdown": float(metrics.get("max_drawdown", metrics.get("max_dd", current.get("max_drawdown", 0.0)))),
                "win_rate": float(metrics.get("win_rate", current.get("win_rate", 0.0))),
                "expectancy": float(metrics.get("expectancy", current.get("expectancy", 0.0))),
                "sample_size": int(metrics.get("sample_size", current.get("sample_size", 0))),
                "returns": list(metrics.get("returns", current.get("returns", []))),
            }
        )
        self._items[strategy_id] = current
        self.save()
        return current
