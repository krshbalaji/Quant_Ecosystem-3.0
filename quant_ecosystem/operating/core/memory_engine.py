from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryEngine:
    """Persists long-horizon runtime memory for regime, event, and strategy behavior."""

    def __init__(self, root: str | Path = "storage/memory") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.regime_path = self.root / "regime_history.json"
        self.event_path = self.root / "event_memory.json"
        self.strategy_path = self.root / "strategy_performance_history.json"

    def record_regime(self, regime: str, context: dict[str, Any] | None = None) -> None:
        self._append(
            self.regime_path,
            {
                "ts": self._now(),
                "regime": str(regime or "UNKNOWN").upper(),
                "context": context or {},
            },
        )

    def record_event(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self._append(
            self.event_path,
            {
                "ts": self._now(),
                "event_type": str(event_type or "NONE").upper(),
                "payload": payload or {},
            },
        )

    def record_strategy_snapshot(self, strategy_id: str, metrics: dict[str, Any] | None = None) -> None:
        self._append(
            self.strategy_path,
            {
                "ts": self._now(),
                "strategy_id": str(strategy_id or "UNKNOWN"),
                "metrics": metrics or {},
            },
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "regime_history": self._load(self.regime_path),
            "event_memory": self._load(self.event_path),
            "strategy_performance": self._load(self.strategy_path),
        }

    def _append(self, path: Path, row: dict[str, Any]) -> None:
        payload = self._load(path)
        payload.append(row)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _load(self, path: Path) -> list[dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, list) else []
        except Exception:
            return []

    def _now(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
