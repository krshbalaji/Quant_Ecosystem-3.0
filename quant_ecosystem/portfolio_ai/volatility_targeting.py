"""Volatility targeting controls for portfolio allocations."""

from __future__ import annotations

from typing import Dict, Iterable, List


class VolatilityTargeting:
    """Scales allocations to maintain target portfolio volatility."""

    def __init__(self, target_volatility: float = 0.10, min_scale: float = 0.4, max_scale: float = 1.6, **kwargs):
        self.target_volatility = max(0.01, float(target_volatility))
        self.min_scale = max(0.05, float(min_scale))
        self.max_scale = max(self.min_scale, float(max_scale))

    def scale_allocations(
        self,
        allocations: Dict[str, float],
        strategy_rows: Iterable[Dict],
    ) -> Dict:
        rows = [dict(row) for row in strategy_rows if row.get("id")]
        current_vol = self._portfolio_volatility(allocations, rows)
        if current_vol <= 1e-9:
            return {
                "allocations": dict(allocations),
                "portfolio_volatility": 0.0,
                "scale_factor": 1.0,
            }

        raw_scale = self.target_volatility / current_vol
        scale = max(self.min_scale, min(self.max_scale, raw_scale))
        scaled = {sid: round(float(w) * scale, 6) for sid, w in allocations.items()}
        normalized = self._normalize_to_100(scaled)
        return {
            "allocations": normalized,
            "portfolio_volatility": round(current_vol, 6),
            "scale_factor": round(scale, 6),
        }

    def _portfolio_volatility(self, allocations: Dict[str, float], rows: List[Dict]) -> float:
        by_id = {str(row.get("id")): row for row in rows}
        variance = 0.0
        for sid, weight_pct in allocations.items():
            row = by_id.get(str(sid), {})
            vol = self._volatility(row)
            w = float(weight_pct) / 100.0
            variance += (w * vol) ** 2
        return variance ** 0.5

    def _volatility(self, row: Dict) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        returns = metrics.get("returns", row.get("returns", []))
        vals: List[float] = []
        for item in returns or []:
            try:
                vals.append(float(item))
            except (TypeError, ValueError):
                continue
        if len(vals) < 2:
            fallback = float(metrics.get("volatility", row.get("volatility", 0.20)))
            return max(0.01, abs(fallback))
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / max(1, len(vals) - 1)
        return max(0.01, var ** 0.5)

    def _normalize_to_100(self, allocations: Dict[str, float]) -> Dict[str, float]:
        total = sum(max(0.0, float(v)) for v in allocations.values())
        if total <= 1e-9:
            return {k: 0.0 for k in allocations}
        return {k: round((max(0.0, float(v)) / total) * 100.0, 6) for k, v in allocations.items()}

