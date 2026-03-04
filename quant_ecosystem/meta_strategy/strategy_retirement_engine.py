"""Retirement engine for strategy archive and deactivation decisions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


class StrategyRetirementEngine:
    """Retires strategies based on hard deterioration and decay signals."""

    def __init__(
        self,
        drawdown_threshold: float = 20.0,
        min_sharpe: float = 0.0,
        min_profit_factor: float = 1.0,
        min_meta_score: float = 0.30,
        archive_dir: str = "strategy_archive",
    ):
        self.drawdown_threshold = float(drawdown_threshold)
        self.min_sharpe = float(min_sharpe)
        self.min_profit_factor = float(min_profit_factor)
        self.min_meta_score = float(min_meta_score)
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, strategy_rows: Iterable[Dict]) -> Dict:
        """Returns retirement decisions and archives retired strategies."""
        retired: List[Dict] = []
        survivors: List[Dict] = []
        for row in strategy_rows:
            should_retire, reason = self._should_retire(row)
            if should_retire:
                item = dict(row)
                item["retirement_reason"] = reason
                item["stage"] = "RETIRED"
                self._archive(item)
                retired.append(item)
            else:
                survivors.append(dict(row))
        return {"retired": retired, "survivors": survivors}

    def _should_retire(self, row: Dict) -> tuple[bool, str]:
        dd = self._metric(row, "max_dd", "max_drawdown")
        sharpe = self._metric(row, "sharpe")
        pf = self._metric(row, "profit_factor")
        score = self._float(row.get("meta_score", 0.0))
        returns = self._returns(row)

        if dd > self.drawdown_threshold:
            return True, "drawdown_breach"
        if sharpe < self.min_sharpe:
            return True, "negative_sharpe"
        if pf < self.min_profit_factor:
            return True, "low_profit_factor"
        if score < self.min_meta_score:
            return True, "low_meta_score"
        if self._long_term_decay(returns):
            return True, "long_term_decay"
        return False, "healthy"

    def _archive(self, row: Dict) -> None:
        sid = str(row.get("id", "unknown")).strip() or "unknown"
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.archive_dir / f"{sid}_{ts}.json"
        payload = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "strategy": row,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _long_term_decay(self, returns: List[float]) -> bool:
        if len(returns) < 60:
            return False
        head = returns[-60:-30]
        tail = returns[-30:]
        head_mean = sum(head) / max(1, len(head))
        tail_mean = sum(tail) / max(1, len(tail))
        return tail_mean < (head_mean * 0.5) and tail_mean < 0.0

    def _returns(self, row: Dict) -> List[float]:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        src = metrics.get("returns", row.get("returns", []))
        out = []
        for value in src or []:
            try:
                out.append(float(value))
            except (TypeError, ValueError):
                continue
        return out[-200:]

    def _metric(self, row: Dict, primary: str, fallback: str | None = None) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        if primary in metrics:
            return self._float(metrics.get(primary))
        if primary in row:
            return self._float(row.get(primary))
        if fallback:
            if fallback in metrics:
                return self._float(metrics.get(fallback))
            if fallback in row:
                return self._float(row.get(fallback))
        return 0.0

    def _float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

