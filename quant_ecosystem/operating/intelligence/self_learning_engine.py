from __future__ import annotations

from typing import Any, Dict


class SelfLearningEngine:
    """Lightweight daily strategy promotion/demotion layer."""

    def __init__(self, config: Any = None, **kwargs) -> None:
        self.config = config

    def evaluate(self, performance_log: Dict[str, Dict] | None = None) -> Dict[str, Any]:
        performance_log = dict(performance_log or {})
        promote = []
        reduce = []
        allocation_bias = {}

        for sid, row in performance_log.items():
            win_rate = float(row.get("win_rate", 0.0) or 0.0)
            avg_pnl = float(row.get("avg_pnl", 0.0) or 0.0)
            if win_rate >= 55.0 and avg_pnl >= 0.0:
                promote.append(sid)
                allocation_bias[sid] = 1.2
            elif win_rate < 45.0 or avg_pnl < 0.0:
                reduce.append(sid)
                allocation_bias[sid] = 0.8

        return {
            "promote": promote,
            "reduce": reduce,
            "allocation_bias": allocation_bias,
            "summary": f"promote={len(promote)} reduce={len(reduce)}",
        }
