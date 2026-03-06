"""Dynamic capital allocation engine."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from quant_ecosystem.capital_allocator.exposure_controller import ExposureController
from quant_ecosystem.capital_allocator.rebalance_manager import RebalanceManager
from quant_ecosystem.capital_allocator.risk_adjusted_allocator import RiskAdjustedAllocator


class CapitalAllocator:
    """Main allocator coordinating scoring, exposure controls, and rebalancing."""

    def __init__(
        self,
        strategy_bank_layer=None,
        strategy_selector=None,
        risk_adjusted_allocator: Optional[RiskAdjustedAllocator] = None,
        exposure_controller: Optional[ExposureController] = None,
        rebalance_manager: Optional[RebalanceManager] = None,
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.strategy_selector = strategy_selector
        self.risk_adjusted_allocator = risk_adjusted_allocator or RiskAdjustedAllocator()
        self.exposure_controller = exposure_controller or ExposureController()
        self.rebalance_manager = rebalance_manager or RebalanceManager(interval_minutes=30)
        self.last_allocation: Dict[str, float] = {}

    def allocate_capital(
        self,
        regime: str,
        strategy_rows: Optional[Iterable[Dict]] = None,
        capital_available_pct: float = 100.0,
        current_drawdown_pct: float = 0.0,
    ) -> Dict:
        rows = list(strategy_rows) if strategy_rows is not None else self._fetch_rows()
        selected_rows = self._filter_by_selector(regime, rows, capital_available_pct)
        proposed = self.risk_adjusted_allocator.allocate(selected_rows, capital_available_pct=capital_available_pct)
        final_alloc, diagnostics = self.exposure_controller.apply_limits(
            proposed_allocations=proposed,
            strategy_rows=selected_rows,
            current_drawdown_pct=current_drawdown_pct,
        )
        self.last_allocation = dict(final_alloc)
        self._publish_to_bank(final_alloc)
        return {
            "regime": str(regime).upper(),
            "proposed": proposed,
            "allocation": final_alloc,
            "diagnostics": diagnostics,
            "selected_count": len(selected_rows),
        }

    def rebalance(
        self,
        regime: str,
        strategy_rows: Optional[Iterable[Dict]] = None,
        capital_available_pct: float = 100.0,
        current_drawdown_pct: float = 0.0,
        force: bool = False,
    ) -> Dict:
        if not force and not self.rebalance_manager.should_rebalance(regime):
            return {
                "rebalanced": False,
                "reason": "NOT_DUE",
                "allocation": dict(self.last_allocation),
            }
        result = self.allocate_capital(
            regime=regime,
            strategy_rows=strategy_rows,
            capital_available_pct=capital_available_pct,
            current_drawdown_pct=current_drawdown_pct,
        )
        self.rebalance_manager.mark_rebalanced(regime=regime)
        result["rebalanced"] = True
        return result

    def reduce_exposure(self, reduction_pct: float = 20.0) -> Dict[str, float]:
        """Reduces current allocation proportionally for defensive posture."""
        cut = max(0.0, min(100.0, float(reduction_pct)))
        factor = max(0.0, 1.0 - (cut / 100.0))
        reduced = {sid: round(value * factor, 4) for sid, value in self.last_allocation.items()}
        self.last_allocation = reduced
        self._publish_to_bank(reduced)
        return reduced

    def _fetch_rows(self):
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                return list(layer.registry_rows())
            except Exception:
                return []
        return []

    def _filter_by_selector(self, regime: str, rows: Iterable[Dict], capital_available_pct: float):
        selector = self.strategy_selector
        if selector is None:
            return list(rows)
        try:
            out = selector.select(
                market_regime=str(regime).upper(),
                risk_limits={
                    "max_drawdown": self.exposure_controller.max_portfolio_drawdown,
                    "min_profit_factor": 0.8,
                    "min_sharpe": -5.0,
                },
                capital_available_pct=capital_available_pct,
            )
            selected_ids = {str(row.get("id")) for row in out.get("selected", []) if row.get("id")}
            if not selected_ids:
                return list(rows)
            return [row for row in rows if str(row.get("id")) in selected_ids]
        except Exception:
            return list(rows)

    def _publish_to_bank(self, allocation: Dict[str, float]) -> None:
        layer = self.strategy_bank_layer
        if not layer or not hasattr(layer, "is_enabled") or not layer.is_enabled():
            return
        try:
            rows = layer.registry_rows()
        except Exception:
            rows = []
        for row in rows:
            sid = str(row.get("id", "")).strip()
            if not sid:
                continue
            updated = dict(row)
            updated["allocation_pct"] = float(allocation.get(sid, 0.0))
            layer.bank_engine.registry.upsert(updated)
        layer.bank_engine.registry.save()



# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class AllocationEngine:
    """Minimal SystemFactory entry-point for capital allocation.

    Delegates to :class:`CapitalAllocator` when available; otherwise
    returns the input strategy list with equal weight.
    """

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = CapitalAllocator()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("AllocationEngine: delegate unavailable (%s) — stub mode", exc)
        self._log.info("AllocationEngine initialized")

    def allocate(self, strategies: list, total_capital: float = 0.0) -> list:
        """Allocate *total_capital* across *strategies*.

        Returns strategies annotated with ``capital_fraction``; on error
        returns the input list unchanged.
        """
        if self._delegate is not None:
            try:
                return self._delegate.allocate_capital(
                    strategies=strategies, total_capital=total_capital
                )
            except Exception as exc:  # noqa: BLE001
                self._log.warning("AllocationEngine.allocate: delegate error (%s)", exc)
        # Equal-weight stub
        n = len(strategies)
        fraction = 1.0 / n if n else 0.0
        for s in strategies:
            if isinstance(s, dict):
                s.setdefault("capital_fraction", fraction)
        return strategies
