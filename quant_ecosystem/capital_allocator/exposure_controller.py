"""Exposure limits for strategy and portfolio capital controls."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


class ExposureController:
    """Enforces allocation caps and drawdown guardrails."""

    def __init__(
        self,
        max_strategy_allocation: float = 25.0,
        max_sector_exposure: float = 40.0,
        max_portfolio_drawdown: float = 20.0, **kwargs
    ):
        self.max_strategy_allocation = float(max_strategy_allocation)
        self.max_sector_exposure = float(max_sector_exposure)
        self.max_portfolio_drawdown = float(max_portfolio_drawdown)

    def apply_limits(
        self,
        proposed_allocations: Dict[str, float],
        strategy_rows: Iterable[Dict],
        current_drawdown_pct: float = 0.0,
    ) -> Tuple[Dict[str, float], Dict]:
        """Apply strategy and sector caps to proposed allocations."""
        diagnostics = {
            "reduced_for_strategy_cap": [],
            "reduced_for_sector_cap": [],
            "drawdown_cut_applied": False,
        }

        capped = {}
        for sid, value in proposed_allocations.items():
            bounded = min(float(value), self.max_strategy_allocation)
            if bounded < float(value):
                diagnostics["reduced_for_strategy_cap"].append(sid)
            capped[sid] = round(max(0.0, bounded), 4)

        sector_map = self._sector_map(strategy_rows)
        sector_totals: Dict[str, float] = {}
        for sid, alloc in capped.items():
            sector = sector_map.get(sid, "unknown")
            sector_totals[sector] = sector_totals.get(sector, 0.0) + alloc

        for sector, total in list(sector_totals.items()):
            if total <= self.max_sector_exposure:
                continue
            scale = self.max_sector_exposure / max(total, 1e-9)
            for sid, alloc in list(capped.items()):
                if sector_map.get(sid, "unknown") != sector:
                    continue
                new_alloc = round(alloc * scale, 4)
                if new_alloc < alloc:
                    diagnostics["reduced_for_sector_cap"].append(sid)
                capped[sid] = new_alloc

        drawdown = float(current_drawdown_pct or 0.0)
        if drawdown >= self.max_portfolio_drawdown:
            diagnostics["drawdown_cut_applied"] = True
            for sid in list(capped.keys()):
                capped[sid] = round(capped[sid] * 0.5, 4)

        capped = self._renormalize(capped)
        diagnostics["final_total_pct"] = round(sum(capped.values()), 4)
        return capped, diagnostics

    def _sector_map(self, rows: Iterable[Dict]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for row in rows:
            sid = str(row.get("id", "")).strip()
            if not sid:
                continue
            sector = str(row.get("sector", row.get("asset_class", "unknown"))).strip().lower()
            out[sid] = sector or "unknown"
        return out

    def _renormalize(self, allocs: Dict[str, float]) -> Dict[str, float]:
        total = sum(float(v) for v in allocs.values())
        if total <= 0:
            return {}
        scale = 100.0 / total if total > 100.0 else 1.0
        return {sid: round(max(0.0, float(value) * scale), 4) for sid, value in allocs.items()}

