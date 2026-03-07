"""Strategy replacement and retirement management."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


class StrategyReplacementManager:
    """Handles LIVE->REDUCED->RETIRED transitions and replacement search."""

    def __init__(
        self,
        archive_dir: str = "strategy_archive",
        reduction_factor: float = 0.5,
        min_replacement_sharpe: float = 1.0,
        min_replacement_profit_factor: float = 1.2,
        max_replacement_drawdown: float = 25.0, **kwargs
    ):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.reduction_factor = max(0.1, min(0.9, float(reduction_factor)))
        self.min_replacement_sharpe = float(min_replacement_sharpe)
        self.min_replacement_profit_factor = float(min_replacement_profit_factor)
        self.max_replacement_drawdown = float(max_replacement_drawdown)

    def apply(
        self,
        strategy_row: Dict,
        decay_report: Dict,
        replacement_pool: Iterable[Dict],
        existing_ids: Optional[set] = None,
    ) -> Dict:
        """Apply lifecycle action for one strategy and propose replacement."""
        row = dict(strategy_row)
        stage = str(row.get("stage", "PAPER")).upper()
        allocation = self._f(row.get("allocation_pct", 0.0))
        sid = str(row.get("id", "")).strip()
        if not sid:
            return {"action": "SKIP_INVALID", "row": row, "replacement": None}

        if not decay_report.get("is_decaying", False):
            return {"action": "STABLE", "row": row, "replacement": None}

        action = "REDUCE"
        if stage in {"LIVE", "PAPER", "SHADOW"}:
            row["stage"] = "REDUCED"
            row["active"] = False
            row["allocation_pct"] = round(allocation * self.reduction_factor, 6)
            row["survival_status"] = "DECAY_REDUCED"
            row["survival_reason"] = ",".join(decay_report.get("reasons", []))
        elif stage == "REDUCED":
            row["stage"] = "RETIRED"
            row["active"] = False
            row["allocation_pct"] = 0.0
            row["survival_status"] = "DECAY_RETIRED"
            row["survival_reason"] = ",".join(decay_report.get("reasons", []))
            self._archive_strategy(row, decay_report)
            action = "RETIRE"
        elif stage == "RETIRED":
            action = "ALREADY_RETIRED"
            row["active"] = False
            row["allocation_pct"] = 0.0
        else:
            row["stage"] = "REDUCED"
            row["active"] = False
            row["allocation_pct"] = round(allocation * self.reduction_factor, 6)
            action = "REDUCE"

        replacement = None
        if action in {"REDUCE", "RETIRE"}:
            replacement = self._find_replacement(
                replacement_pool=replacement_pool,
                asset_class=str(row.get("asset_class", "stocks")),
                timeframe=str(row.get("timeframe", "5m")),
                existing_ids=existing_ids or set(),
            )

        return {
            "action": action,
            "row": row,
            "replacement": replacement,
        }

    def _find_replacement(self, replacement_pool: Iterable[Dict], asset_class: str, timeframe: str, existing_ids: set) -> Optional[Dict]:
        candidates: List[Dict] = []
        for item in replacement_pool:
            sid = str(item.get("id", "")).strip()
            if not sid or sid in existing_ids:
                continue
            metrics = dict(item.get("metrics", item.get("performance_metrics", {})))
            sharpe = self._f(metrics.get("sharpe", item.get("sharpe", 0.0)))
            pf = self._f(metrics.get("profit_factor", item.get("profit_factor", 0.0)))
            dd = self._f(metrics.get("max_dd", metrics.get("max_drawdown", item.get("max_drawdown", 0.0))))
            if sharpe < self.min_replacement_sharpe:
                continue
            if pf < self.min_replacement_profit_factor:
                continue
            if dd > self.max_replacement_drawdown:
                continue
            row = dict(item)
            row["metrics"] = metrics
            score = (0.45 * sharpe) + (0.35 * pf) - (0.20 * dd / 10.0)
            # Prefer asset/timeframe affinity where available.
            if str(row.get("asset_class", "")).lower() == asset_class.lower():
                score += 0.2
            if str(row.get("timeframe", "")).lower() == timeframe.lower():
                score += 0.1
            row["_replacement_score"] = score
            candidates.append(row)

        if not candidates:
            return None
        best = sorted(candidates, key=lambda x: float(x.get("_replacement_score", 0.0)), reverse=True)[0]
        best["stage"] = "SHADOW"
        best["active"] = False
        best["allocation_pct"] = 0.0
        best["replacement_candidate"] = True
        return best

    def _archive_strategy(self, row: Dict, decay_report: Dict) -> None:
        sid = str(row.get("id", "unknown")).strip() or "unknown"
        payload = dict(row)
        payload["retired_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        payload["decay_report"] = dict(decay_report)
        path = self.archive_dir / f"{sid}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

