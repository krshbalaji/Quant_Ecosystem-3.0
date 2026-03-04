"""Lifecycle transitions for institutional strategy management."""

from __future__ import annotations

from typing import Dict, Tuple


class LifecycleManager:
    """Applies stage transitions using objective risk/performance gates."""

    STAGES = ("CANDIDATE", "BACKTESTED", "PAPER", "SHADOW", "LIVE", "RETIRED")

    def __init__(self, min_trades_for_promotion: int = 100, retire_dd_threshold: float = 20.0):
        self.min_trades_for_promotion = int(max(10, min_trades_for_promotion))
        self.retire_dd_threshold = float(max(5.0, retire_dd_threshold))

    def evaluate(self, meta: Dict) -> Tuple[str, str]:
        stage = str(meta.get("stage", "CANDIDATE")).upper()
        profit_factor = float(meta.get("profit_factor", 0.0))
        drawdown = float(meta.get("max_drawdown", 0.0))
        sharpe = float(meta.get("sharpe", 0.0))
        sample_size = int(meta.get("sample_size", 0))

        if stage == "LIVE" and profit_factor < 1.0 and drawdown > self.retire_dd_threshold:
            return "RETIRED", "LIVE performance degraded (PF < 1 and DD breached)."

        if stage in {"CANDIDATE", "BACKTESTED"}:
            if self._passes_backtest_gate(meta):
                return "PAPER", "Candidate met backtest gate."
            return stage, "Backtest gate not met."

        if stage == "PAPER":
            if sample_size >= max(20, self.min_trades_for_promotion // 2) and self._is_stable(meta):
                return "SHADOW", "Paper stability achieved."
            return "PAPER", "Waiting for paper stability window."

        if stage == "SHADOW":
            if sample_size >= self.min_trades_for_promotion and self._is_stable(meta):
                return "LIVE", "Shadow strategy promoted to live."
            return "SHADOW", "Shadow sample below promotion threshold."

        if stage == "RETIRED":
            return "RETIRED", "Retired stage is terminal."

        return stage, "No lifecycle change."

    def _passes_backtest_gate(self, meta: Dict) -> bool:
        return (
            float(meta.get("sharpe", 0.0)) >= 1.0
            and float(meta.get("profit_factor", 0.0)) >= 1.1
            and float(meta.get("max_drawdown", 100.0)) < 20.0
            and float(meta.get("expectancy", 0.0)) > 0.0
        )

    def _is_stable(self, meta: Dict) -> bool:
        return (
            float(meta.get("profit_factor", 0.0)) >= 1.15
            and float(meta.get("sharpe", 0.0)) >= 1.2
            and float(meta.get("max_drawdown", 100.0)) < 15.0
            and float(meta.get("expectancy", 0.0)) > 0.0
        )
