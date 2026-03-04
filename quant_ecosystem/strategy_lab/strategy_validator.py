"""Validation gate for Strategy Lab outputs."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


class StrategyValidator:
    """Applies strict promotion/rejection rules to evaluated strategies."""

    def __init__(
        self,
        max_drawdown: float = 25.0,
        min_profit_factor: float = 1.2,
        min_sharpe: float = 1.0,
        min_sample_size: int = 80,
    ):
        self.max_drawdown = float(max_drawdown)
        self.min_profit_factor = float(min_profit_factor)
        self.min_sharpe = float(min_sharpe)
        self.min_sample_size = max(1, int(min_sample_size))

    def validate(self, strategies: Iterable[Dict]) -> Dict:
        """Returns validated/rejected strategy lists."""
        valid: List[Dict] = []
        rejected: List[Dict] = []
        for row in strategies:
            ok, reason = self._is_valid(row)
            item = dict(row)
            item["validation_reason"] = reason
            if ok:
                item["stage"] = "SHADOW"
                valid.append(item)
            else:
                item["stage"] = "RESEARCH"
                rejected.append(item)
        return {"validated": valid, "rejected": rejected}

    def _is_valid(self, row: Dict) -> Tuple[bool, str]:
        metrics = row.get("metrics", {})
        dd = self._float(metrics.get("max_dd", metrics.get("max_drawdown", 0.0)))
        pf = self._float(metrics.get("profit_factor", 0.0))
        sharpe = self._float(metrics.get("sharpe", 0.0))
        sample = int(self._float(metrics.get("sample_size", len(metrics.get("returns", [])))))

        if dd > self.max_drawdown:
            return False, "max_drawdown_exceeded"
        if pf < self.min_profit_factor:
            return False, "profit_factor_below_threshold"
        if sharpe < self.min_sharpe:
            return False, "sharpe_below_threshold"
        if sample < self.min_sample_size:
            return False, "sample_size_too_low"
        return True, "validated"

    def _float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

