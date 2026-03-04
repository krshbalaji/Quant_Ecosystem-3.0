"""Persistence layer for Strategy Lab artifacts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


class StrategyRepository:
    """Stores research, validated, and archived strategy artifacts."""

    def __init__(self, base_dir: str = "strategy_lab"):
        self.base_dir = Path(base_dir)
        self.research_dir = self.base_dir / "research_strategies"
        self.validated_dir = self.base_dir / "validated_strategies"
        self.archived_dir = self.base_dir / "archived_strategies"
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.validated_dir.mkdir(parents=True, exist_ok=True)
        self.archived_dir.mkdir(parents=True, exist_ok=True)

    def save_research(self, rows: Iterable[Dict]) -> List[str]:
        return self._save_batch(rows, self.research_dir)

    def save_validated(self, rows: Iterable[Dict]) -> List[str]:
        return self._save_batch(rows, self.validated_dir)

    def archive(self, rows: Iterable[Dict]) -> List[str]:
        return self._save_batch(rows, self.archived_dir)

    def _save_batch(self, rows: Iterable[Dict], folder: Path) -> List[str]:
        paths = []
        for row in rows:
            sid = str(row.get("id", "")).strip()
            if not sid:
                sid = f"strategy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            payload = dict(row)
            payload.setdefault("strategy_name", sid)
            payload.setdefault("creation_date", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
            payload.setdefault("strategy_type", payload.get("family", payload.get("category", "unknown")))
            payload.setdefault("indicators_used", list(payload.get("indicators", [])))
            payload.setdefault("performance_metrics", dict(payload.get("metrics", {})))
            payload.setdefault("mutation_origin", payload.get("metadata", {}).get("mutation_origin", "unknown"))
            path = folder / f"{sid}.json"
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            paths.append(str(path))
        return paths

