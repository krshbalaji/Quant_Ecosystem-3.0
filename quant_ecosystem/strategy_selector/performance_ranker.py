"""Performance ranking engine for strategy selector."""

from __future__ import annotations

from typing import Dict, Iterable, List


class PerformanceRanker:
    """Ranks strategies by quality-adjusted performance and risk controls."""

    def __init__(
        self,
        weight_sharpe: float = 0.35,
        weight_win_rate: float = 0.20,
        weight_drawdown: float = 0.20,
        weight_profit_factor: float = 0.25,
    ):
        self.weight_sharpe = float(weight_sharpe)
        self.weight_win_rate = float(weight_win_rate)
        self.weight_drawdown = float(weight_drawdown)
        self.weight_profit_factor = float(weight_profit_factor)

    def rank(
        self,
        rows: Iterable[Dict],
        top_n: int = 5,
        risk_limits: Dict | None = None,
        capital_available_pct: float = 100.0,
    ) -> List[Dict]:
        risk_limits = risk_limits or {}
        out: List[Dict] = []
        max_dd = float(risk_limits.get("max_drawdown", 25.0))
        min_pf = float(risk_limits.get("min_profit_factor", 0.8))
        min_sharpe = float(risk_limits.get("min_sharpe", -10.0))

        for row in rows:
            metrics = row.get("metrics", row)
            sharpe = float(metrics.get("sharpe", row.get("sharpe", 0.0)))
            win_rate = float(metrics.get("win_rate", row.get("win_rate", 0.0)))
            drawdown = float(metrics.get("max_dd", metrics.get("max_drawdown", row.get("max_drawdown", 0.0))))
            pf = float(metrics.get("profit_factor", row.get("profit_factor", 0.0)))

            if drawdown > max_dd or pf < min_pf or sharpe < min_sharpe:
                continue

            # Normalized scores.
            sharpe_score = max(0.0, min(sharpe / 3.0, 1.0))
            win_score = max(0.0, min(win_rate / 100.0, 1.0))
            dd_score = 1.0 - max(0.0, min(drawdown / 50.0, 1.0))
            pf_score = max(0.0, min(pf / 3.0, 1.0))

            score = (
                self.weight_sharpe * sharpe_score
                + self.weight_win_rate * win_score
                + self.weight_drawdown * dd_score
                + self.weight_profit_factor * pf_score
            )

            item = dict(row)
            item["selection_score"] = round(score * 100.0, 4)
            out.append(item)

        out.sort(key=lambda row: float(row.get("selection_score", 0.0)), reverse=True)
        selected = out[: max(0, int(top_n))]

        # Soft-cap capital: avoid selecting more than feasible by allocation footprint.
        feasible: List[Dict] = []
        used = 0.0
        default_alloc = max(100.0 / max(1, len(selected)), 1.0)
        for row in selected:
            # Selection stage should not be blocked by stale allocation snapshots
            # from previous cycles. Use equal provisional weights unless explicit
            # enforced allocation is provided by upstream.
            alloc = float(row.get("enforced_allocation_pct", 0.0) or 0.0)
            if alloc <= 0.0:
                alloc = default_alloc
            if used + alloc > capital_available_pct + 1e-6:
                continue
            feasible.append(row)
            used += alloc
        return feasible
