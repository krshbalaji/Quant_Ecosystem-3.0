from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class StrategyManager:
    """Lightweight governance layer for versioning and strategy lifecycle control."""

    def __init__(self, storage_path: str | Path = "storage/strategy_manager_state.json") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def sync_registry(self, strategy_ids: list[str]) -> dict[str, Any]:
        strategies = self._state.setdefault("strategies", {})
        for strategy_id in strategy_ids:
            bucket = strategies.setdefault(
                str(strategy_id),
                {
                    "strategy_id": str(strategy_id),
                    "enabled": True,
                    "current_version": 1,
                    "history": [],
                    "status": "active",
                    "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            bucket.setdefault("enabled", True)
            bucket.setdefault("status", "active")
        self._save()
        return strategies

    def register_version(self, strategy_id: str, version_note: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        strategy = self._ensure_strategy(strategy_id)
        strategy["current_version"] = int(strategy.get("current_version", 1) or 1) + 1
        strategy["history"].append(
            {
                "version": strategy["current_version"],
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "note": version_note,
                "payload": payload or {},
            }
        )
        strategy["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save()
        return strategy

    def set_enabled(self, strategy_id: str, enabled: bool) -> dict[str, Any]:
        strategy = self._ensure_strategy(strategy_id)
        strategy["enabled"] = bool(enabled)
        strategy["status"] = "active" if enabled else "disabled"
        strategy["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save()
        return strategy

    def assess_performance(self, performance_log: dict[str, Any]) -> dict[str, Any]:
        actions = {"promoted": [], "demoted": []}
        for strategy_id, metrics in dict(performance_log or {}).items():
            strategy = self._ensure_strategy(strategy_id)
            total_pnl = float(metrics.get("total_pnl", 0.0) or 0.0)
            win_rate = float(metrics.get("win_rate", 0.0) or 0.0)
            if total_pnl > 0 and win_rate >= 55.0:
                strategy["status"] = "promoted"
                strategy["enabled"] = True
                actions["promoted"].append(strategy_id)
            elif total_pnl < 0 and win_rate < 45.0:
                strategy["status"] = "demoted"
                actions["demoted"].append(strategy_id)
            strategy["last_metrics"] = metrics
        self._save()
        return actions

    def rollback(self, strategy_id: str) -> dict[str, Any]:
        strategy = self._ensure_strategy(strategy_id)
        history = list(strategy.get("history", []) or [])
        if not history:
            return strategy
        history.pop()
        strategy["history"] = history
        strategy["current_version"] = max(1, int(strategy.get("current_version", 1) or 1) - 1)
        strategy["status"] = "rolled_back"
        strategy["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save()
        return strategy

    def active_strategies(self) -> list[str]:
        return [
            strategy_id
            for strategy_id, payload in dict(self._state.get("strategies", {}) or {}).items()
            if bool(payload.get("enabled", True))
        ]

    def snapshot(self) -> dict[str, Any]:
        return dict(self._state)

    def _ensure_strategy(self, strategy_id: str) -> dict[str, Any]:
        strategies = self._state.setdefault("strategies", {})
        bucket = strategies.setdefault(
            str(strategy_id),
            {
                "strategy_id": str(strategy_id),
                "enabled": True,
                "current_version": 1,
                "history": [],
                "status": "active",
                "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        return bucket

    def _load(self) -> dict[str, Any]:
        try:
            with self.storage_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else {"strategies": {}}
        except Exception:
            return {"strategies": {}}

    def _save(self) -> None:
        with self.storage_path.open("w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)
