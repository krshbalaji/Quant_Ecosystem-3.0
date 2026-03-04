"""Lifecycle transitions for meta strategy governance."""

from __future__ import annotations

from typing import Dict, Tuple


class StrategyLifecycleManager:
    """Manages stage transitions across RESEARCH..RETIRED states."""

    VALID_STAGES = {"RESEARCH", "SHADOW", "PAPER", "LIVE", "REDUCED", "RETIRED"}

    def __init__(
        self,
        promote_to_shadow_score: float = 0.45,
        promote_to_paper_score: float = 0.55,
        promote_to_live_score: float = 0.65,
        reduce_live_score: float = 0.40,
        retire_reduced_score: float = 0.30,
        min_trades_live: int = 100,
    ):
        self.promote_to_shadow_score = float(promote_to_shadow_score)
        self.promote_to_paper_score = float(promote_to_paper_score)
        self.promote_to_live_score = float(promote_to_live_score)
        self.reduce_live_score = float(reduce_live_score)
        self.retire_reduced_score = float(retire_reduced_score)
        self.min_trades_live = max(1, int(min_trades_live))

    def transition(self, strategy_row: Dict) -> Tuple[str, str]:
        """Returns `(next_stage, reason)` for a strategy."""
        stage = str(strategy_row.get("stage", "RESEARCH")).upper()
        score = self._float(strategy_row.get("meta_score", 0.0))
        sample_size = int(self._metric(strategy_row, "sample_size"))
        pf = self._metric(strategy_row, "profit_factor")
        sharpe = self._metric(strategy_row, "sharpe")
        dd = self._metric(strategy_row, "max_dd", "max_drawdown")

        if stage not in self.VALID_STAGES:
            stage = "RESEARCH"

        if stage == "RETIRED":
            return "RETIRED", "already_retired"

        if pf < 1.0 and dd > 20.0:
            return "RETIRED", "risk_floor_breach"

        if stage == "RESEARCH":
            if score >= self.promote_to_shadow_score:
                return "SHADOW", "research_validated"
            return "RESEARCH", "await_research_validation"

        if stage == "SHADOW":
            if score >= self.promote_to_paper_score and sample_size >= max(20, self.min_trades_live // 5):
                return "PAPER", "shadow_validated"
            if score < self.retire_reduced_score and sample_size >= 20:
                return "RETIRED", "shadow_decay"
            return "SHADOW", "collect_shadow_evidence"

        if stage == "PAPER":
            if score >= self.promote_to_live_score and sample_size >= self.min_trades_live:
                return "LIVE", "paper_promoted"
            if score < self.retire_reduced_score and sample_size >= max(30, self.min_trades_live // 2):
                return "RETIRED", "paper_decay"
            return "PAPER", "collect_paper_evidence"

        if stage == "LIVE":
            if score < self.reduce_live_score or sharpe < 0.0:
                return "REDUCED", "live_degraded"
            return "LIVE", "live_healthy"

        if stage == "REDUCED":
            if score >= self.promote_to_live_score and sharpe >= 0.5:
                return "LIVE", "recovery_confirmed"
            if score < self.retire_reduced_score or (pf < 1.0 and dd > 15.0):
                return "RETIRED", "continued_decay"
            return "REDUCED", "monitor_recovery"

        return stage, "no_change"

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

