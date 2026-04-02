"""Persistent cognitive memory."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class CognitiveMemory:
    """Stores historical cognitive state snapshots and stress patterns."""

    def __init__(self, path: str = "quant_ecosystem/cognitive_control/memory/cognitive_memory.json", **kwargs):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def append_state(self, state: Dict) -> None:
        row = dict(state)
        row.setdefault("timestamp", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        self._data.setdefault("states", [])
        self._data["states"] = (self._data["states"] + [row])[-5000:]
        self._track_patterns(row)

    def recent_states(self, n: int = 200) -> List[Dict]:
        return list(self._data.get("states", []))[-max(1, int(n)) :]

    def summary(self) -> Dict:
        rows = self.recent_states(500)
        if not rows:
            return {"stress_events": 0, "regime_transitions": 0, "avg_drawdown": 0.0}
        avg_drawdown = sum(float(item.get("portfolio_drawdown", 0.0)) for item in rows) / len(rows)
        return {
            "stress_events": int(self._data.get("stress_events", 0)),
            "regime_transitions": int(self._data.get("regime_transitions", 0)),
            "avg_drawdown": round(avg_drawdown, 6),
        }

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _track_patterns(self, row: Dict) -> None:
        if float(row.get("portfolio_drawdown", 0.0)) >= 10.0:
            self._data["stress_events"] = int(self._data.get("stress_events", 0)) + 1
        regime = str(row.get("regime", "UNKNOWN")).upper()
        prev = str(self._data.get("last_regime", regime)).upper()
        if regime != prev:
            self._data["regime_transitions"] = int(self._data.get("regime_transitions", 0)) + 1
        self._data["last_regime"] = regime

    def _load(self) -> Dict:
        if not self.path.exists():
            return {"states": [], "stress_events": 0, "regime_transitions": 0, "last_regime": "UNKNOWN"}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("states", [])
                payload.setdefault("stress_events", 0)
                payload.setdefault("regime_transitions", 0)
                payload.setdefault("last_regime", "UNKNOWN")
                return payload
        except Exception:
            pass
        return {"states": [], "stress_events": 0, "regime_transitions": 0, "last_regime": "UNKNOWN"}

