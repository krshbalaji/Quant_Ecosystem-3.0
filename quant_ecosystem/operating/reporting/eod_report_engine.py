from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class EODReportEngine:
    """Produces a lightweight intelligent EOD summary."""

    def __init__(self, output_dir: str = "storage", **kwargs) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, state: Any, performance_log: Dict[str, Dict] | None = None, lessons: List[str] | None = None) -> Dict[str, Any]:
        performance_log = dict(performance_log or {})
        lessons = list(lessons or [])
        ordered = sorted(performance_log.values(), key=lambda row: float(row.get("total_pnl", 0.0)), reverse=True)
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_pnl": round(float(getattr(state, "realized_pnl", 0.0) or 0.0), 2),
            "win_rate": round(self._portfolio_win_rate(performance_log), 2),
            "best_strategy": ordered[0]["strategy_id"] if ordered else "N/A",
            "worst_strategy": ordered[-1]["strategy_id"] if ordered else "N/A",
            "lessons": lessons or ["Stay selective when confidence is weak."],
        }
        out = self.output_dir / "eod_intelligence_report.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def _portfolio_win_rate(self, performance_log: Dict[str, Dict]) -> float:
        trades = sum(int(row.get("trades", 0) or 0) for row in performance_log.values())
        wins = sum(int(row.get("wins", 0) or 0) for row in performance_log.values())
        if trades <= 0:
            return 0.0
        return (wins / trades) * 100.0
