"""Genome library storage for Alpha Genome Engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AlphaGenome:
    """Structured strategy genome."""

    genome_id: str
    market_filter_gene: Dict
    signal_gene: Dict
    entry_gene: Dict
    exit_gene: Dict
    risk_gene: Dict
    execution_gene: Dict
    metadata: Dict = field(default_factory=dict)


class AlphaGenomeLibrary:
    """Persistent storage and retrieval for strategy genomes."""

    def __init__(self, path: str = "quant_ecosystem/alpha_genome/data/genome_library.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rows = self._load()

    def upsert(self, genome: AlphaGenome) -> Dict:
        payload = asdict(genome)
        payload.setdefault("metadata", {})
        payload["metadata"]["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        existing = next((i for i, row in enumerate(self._rows) if row.get("genome_id") == genome.genome_id), None)
        if existing is None:
            payload["metadata"].setdefault("created_at", payload["metadata"]["updated_at"])
            self._rows.append(payload)
        else:
            self._rows[existing] = payload
        self.save()
        return payload

    def upsert_dict(self, genome_payload: Dict) -> Dict:
        payload = dict(genome_payload or {})
        genome = AlphaGenome(
            genome_id=str(payload.get("genome_id", "")),
            market_filter_gene=dict(payload.get("market_filter_gene", {}) or {}),
            signal_gene=dict(payload.get("signal_gene", {}) or {}),
            entry_gene=dict(payload.get("entry_gene", {}) or {}),
            exit_gene=dict(payload.get("exit_gene", {}) or {}),
            risk_gene=dict(payload.get("risk_gene", {}) or {}),
            execution_gene=dict(payload.get("execution_gene", {}) or {}),
            metadata=dict(payload.get("metadata", {}) or {}),
        )
        return self.upsert(genome)

    def get(self, genome_id: str) -> Optional[Dict]:
        gid = str(genome_id).strip()
        for row in self._rows:
            if str(row.get("genome_id", "")) == gid:
                return dict(row)
        return None

    def list(self, limit: int = 200) -> List[Dict]:
        take = max(1, int(limit))
        return [dict(row) for row in self._rows[-take:]]

    def delete(self, genome_id: str) -> bool:
        gid = str(genome_id).strip()
        before = len(self._rows)
        self._rows = [row for row in self._rows if str(row.get("genome_id", "")) != gid]
        changed = len(self._rows) != before
        if changed:
            self.save()
        return changed

    def save(self) -> None:
        self.path.write_text(json.dumps(self._rows, indent=2), encoding="utf-8")

    def _load(self) -> List[Dict]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
        except Exception:
            pass
        return []
