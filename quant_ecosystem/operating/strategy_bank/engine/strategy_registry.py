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

    def __init__(self, metadata_path: str = "strategy_bank/metadata/strategy_registry.json", governance_mode=True, **kwargs):
        self.governance_mode = governance_mode
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

    def load(self):
        try:
            return self.get_live_strategies()
        except Exception:
            return {}
    
    def save(self) -> None:
        self.metadata_file.write_text(json.dumps(self._items, indent=2), encoding="utf-8")

    def get(self, strategy_id: str) -> Optional[Dict]:
        return self._items.get(strategy_id)

    def all(self) -> List[Dict]:
        return [self._items[key] for key in sorted(self._items.keys())]

    def upsert(self, row, source="runtime"):
        payload = dict(row or {})
        strategy_id = str(payload.get("id") or payload.get("strategy_id") or "").strip()
        if not strategy_id:
            return None

        current = dict(self._items.get(strategy_id, {}))
        if self.governance_mode and source != "governor" and current:
            preserved = {
                "stage": current.get("stage", payload.get("stage", "CANDIDATE")),
                "active": current.get("active", payload.get("active", False)),
                "allocation_pct": current.get("allocation_pct", payload.get("allocation_pct", 0.0)),
            }
        else:
            preserved = {}

        merged = {
            "id": strategy_id,
            "asset_class": payload.get("asset_class", current.get("asset_class", "stocks")),
            "timeframe": payload.get("timeframe", current.get("timeframe", "5m")),
            "category": payload.get("category", current.get("category", "systematic")),
            "regime_preference": list(payload.get("regime_preference", current.get("regime_preference", [])) or []),
            "sharpe": float(payload.get("sharpe", current.get("sharpe", 0.0)) or 0.0),
            "profit_factor": float(payload.get("profit_factor", current.get("profit_factor", 0.0)) or 0.0),
            "max_drawdown": float(payload.get("max_drawdown", current.get("max_drawdown", 0.0)) or 0.0),
            "win_rate": float(payload.get("win_rate", current.get("win_rate", 0.0)) or 0.0),
            "expectancy": float(payload.get("expectancy", current.get("expectancy", 0.0)) or 0.0),
            "active": bool(payload.get("active", current.get("active", False))),
            "allocation_pct": float(payload.get("allocation_pct", current.get("allocation_pct", 0.0)) or 0.0),
            "correlation_cluster": payload.get("correlation_cluster", current.get("correlation_cluster", "")),
            "stage": str(payload.get("stage", current.get("stage", "CANDIDATE"))).upper(),
            "score": float(payload.get("score", current.get("score", 0.0)) or 0.0),
            "sample_size": int(payload.get("sample_size", current.get("sample_size", 0)) or 0),
            "returns": list(payload.get("returns", current.get("returns", [])) or []),
        }
        merged.update(preserved)
        self._items[strategy_id] = merged
        return merged

    def bulk_upsert(self, rows: Iterable[Dict]) -> None:
        for row in rows:
            self.upsert(row)
        self.save()

    def update_metrics(self, strategy_id: str, metrics: Dict) -> Dict:
        current = self._items.get(strategy_id)
        if not current:
            current = self.upsert({"id": strategy_id}, source="governor")
        if current is None:
            current = {"id": strategy_id}
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

    def get_live_strategies(self) -> Dict[str, callable]:
        return {}
class StrategyRegistry:

    def __init__(self):
        self._registry = {}

    def register(self, strategy_id, strategy_fn):
        self._registry[strategy_id] = strategy_fn

    def load(self):
        return self._registry

    def get_live_strategies(self):
        return self._registry


    def register_discovered(self, name: str, params: dict):

        strategy_id = f"auto_{len(self._strategies)+1}"

        class AutoStrategy(BaseStrategy):
            def generate_signal(self, market_data):
                return None  # placeholder

        obj = AutoStrategy(
            id=strategy_id,
            name=name,
            family="auto_generated",
            params=params,
            required_timeframes=["5m"],
            required_symbols=[],
        )

        self._strategies[obj.id] = obj    
