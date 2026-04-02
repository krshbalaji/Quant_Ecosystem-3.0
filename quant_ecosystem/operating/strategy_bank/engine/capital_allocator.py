"""Capital allocation for active strategy portfolio."""

from __future__ import annotations

from typing import Dict, List


class CapitalAllocator:
    """Allocates <= 100% capital with rank-weighted and capped sizing."""

    def __init__(self, max_per_strategy_pct: float = 30.0, **kwargs):
        self.max_per_strategy_pct = float(max_per_strategy_pct)

    def allocate(self, ranked_rows: List[Dict]) -> Dict[str, float]:
        active = [row for row in ranked_rows if row.get("active")]
        if not active:
            return {}

        score_sum = sum(max(0.0001, float(row.get("score", 0.0))) for row in active)
        provisional = {}
        for row in active:
            strategy_id = row.get("id")
            base = (max(0.0001, float(row.get("score", 0.0))) / score_sum) * 100.0
            provisional[strategy_id] = min(base, self.max_per_strategy_pct)

        total = sum(provisional.values())
        if total <= 0:
            return {}

        scale = 100.0 / total
        out = {}
        for key, value in provisional.items():
            out[key] = round(value * scale, 4)

        overflow = round(sum(out.values()) - 100.0, 4)
        if overflow > 0:
            top = max(out, key=out.get)
            out[top] = round(max(0.0, out[top] - overflow), 4)
        return out
