"""Strategy decay detector."""

from __future__ import annotations

from typing import Dict, List


class DecayDetector:
    """Detects persistent performance decay from rolling metrics."""

    def __init__(
        self,
        sharpe_floor: float = 0.5,
        min_trades: int = 200,
        profit_factor_floor: float = 1.0,
        expectancy_floor: float = 0.0,
        drawdown_expansion_threshold: float = 1.25,
    ):
        self.sharpe_floor = float(sharpe_floor)
        self.min_trades = max(20, int(min_trades))
        self.profit_factor_floor = float(profit_factor_floor)
        self.expectancy_floor = float(expectancy_floor)
        self.drawdown_expansion_threshold = max(1.0, float(drawdown_expansion_threshold))

    def evaluate(self, row: Dict) -> Dict:
        """Return decay state and diagnostics for one strategy row."""
        metrics = dict(row.get("metrics", row.get("raw_metrics", {})))
        sharpe = self._f(metrics.get("sharpe", row.get("sharpe", 0.0)))
        profit_factor = self._f(metrics.get("profit_factor", row.get("profit_factor", 0.0)))
        expectancy = self._f(metrics.get("expectancy", row.get("expectancy", 0.0)))
        max_dd = self._f(metrics.get("max_dd", metrics.get("max_drawdown", row.get("max_drawdown", 0.0))))
        sample_size = int(metrics.get("sample_size", row.get("sample_size", len(metrics.get("returns", row.get("returns", []))))))
        returns = self._returns(metrics.get("returns", row.get("returns", [])))

        drawdown_expansion = self._drawdown_expansion(returns)
        sharpe_breach = (sample_size >= self.min_trades) and (sharpe < self.sharpe_floor)
        pf_breach = profit_factor < self.profit_factor_floor
        exp_breach = expectancy < self.expectancy_floor
        dd_breach = drawdown_expansion > self.drawdown_expansion_threshold or max_dd > 20.0

        risk_score = (
            (0.35 if sharpe_breach else 0.0)
            + (0.25 if pf_breach else 0.0)
            + (0.20 if exp_breach else 0.0)
            + (0.20 if dd_breach else 0.0)
        )
        is_decaying = risk_score >= 0.45

        reasons = []
        if sharpe_breach:
            reasons.append(f"rolling_sharpe<{self.sharpe_floor}")
        if pf_breach:
            reasons.append(f"rolling_profit_factor<{self.profit_factor_floor}")
        if exp_breach:
            reasons.append(f"rolling_expectancy<{self.expectancy_floor}")
        if dd_breach:
            reasons.append("drawdown_expansion")
        if not reasons:
            reasons.append("stable")

        return {
            "is_decaying": bool(is_decaying),
            "risk_score": round(risk_score, 6),
            "sample_size": sample_size,
            "reasons": reasons,
            "metrics": {
                "sharpe": sharpe,
                "profit_factor": profit_factor,
                "expectancy": expectancy,
                "max_drawdown": max_dd,
                "drawdown_expansion": round(drawdown_expansion, 6),
            },
        }

    def _drawdown_expansion(self, returns: List[float]) -> float:
        if len(returns) < 40:
            return 1.0
        mid = len(returns) // 2
        prev_dd = self._max_drawdown(returns[:mid])
        recent_dd = self._max_drawdown(returns[mid:])
        if prev_dd <= 1e-9:
            return 1.0 if recent_dd <= 1e-9 else 2.0
        return recent_dd / prev_dd

    def _max_drawdown(self, returns: List[float]) -> float:
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            equity *= (1.0 + r)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 1e-12 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd * 100.0

    def _returns(self, values) -> List[float]:
        out = []
        for item in values or []:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                continue
        return out[-400:]

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

