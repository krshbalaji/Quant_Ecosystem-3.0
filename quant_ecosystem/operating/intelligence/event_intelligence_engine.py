from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict


class EventIntelligenceEngine:
    """Detects event risk from manual flags and lightweight calendar heuristics."""

    def __init__(self, config: Any = None, **kwargs) -> None:
        self.config = config

    def analyze(self, now: datetime | None = None) -> Dict[str, Any]:
        now = now or datetime.utcnow()
        manual = str(os.getenv("GLOBAL_EVENT_FLAG", "")).strip().upper()
        if manual in {"FED", "WAR", "BUDGET", "POLICY", "BLACK_SWAN"}:
            impact = "HIGH" if manual in {"WAR", "BLACK_SWAN", "FED"} else "MEDIUM"
            return {"event_type": manual, "impact": impact, "event_flag": True}

        weekday = now.weekday()
        if weekday == 3:
            return {"event_type": "CENTRAL_BANK_WINDOW", "impact": "MEDIUM", "event_flag": True}
        if weekday == 0:
            return {"event_type": "POLICY_SCAN", "impact": "LOW", "event_flag": True}
        return {"event_type": "NONE", "impact": "LOW", "event_flag": False}
