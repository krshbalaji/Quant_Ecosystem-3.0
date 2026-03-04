"""Risk parity allocator for strategy portfolios."""

from __future__ import annotations

from typing import Dict, Iterable, List


class RiskParityEngine:
    """Allocates inversely to volatility so risk contributions equalize."""

    def compute_weights(self, strategy_rows: Iterable[Dict], capital_pct: float = 100.0) -> Dict[str, float]:
        rows = [dict(row) for row in strategy_rows if row.get("id")]
        if not rows:
            return {}

        inv_vol: Dict[str, float] = {}
        for row in rows:
            sid = str(row.get("id"))
            vol = self._volatility(row)
            inv_vol[sid] = 1.0 / max(1e-6, vol)

        total = sum(inv_vol.values())
        if total <= 1e-9:
            equal = float(capital_pct) / len(rows)
            return {str(row.get("id")): round(equal, 6) for row in rows}

        return {
            sid: round((inv_vol[sid] / total) * float(capital_pct), 6)
            for sid in inv_vol
        }

    def risk_contributions(self, weights: Dict[str, float], strategy_rows: Iterable[Dict]) -> Dict[str, float]:
        by_id = {str(row.get("id")): dict(row) for row in strategy_rows if row.get("id")}
        contrib = {}
        for sid, w in weights.items():
            row = by_id.get(str(sid), {})
            vol = self._volatility(row)
            contrib[str(sid)] = round(float(w) * vol, 6)
        return contrib

    def _volatility(self, row: Dict) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        returns = metrics.get("returns", row.get("returns", []))
        vals: List[float] = []
        for r in returns or []:
            try:
                vals.append(float(r))
            except (TypeError, ValueError):
                continue
        if len(vals) < 2:
            fallback = float(row.get("volatility", metrics.get("volatility", 0.25)))
            return max(0.01, abs(fallback))
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / max(1, len(vals) - 1)
        return max(0.01, var ** 0.5)

