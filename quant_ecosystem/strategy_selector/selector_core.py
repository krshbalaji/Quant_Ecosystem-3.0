"""Autonomous strategy selector core workflow."""

from __future__ import annotations

from typing import Dict, List, Optional

from quant_ecosystem.strategy_selector.activation_manager import ActivationManager
from quant_ecosystem.strategy_selector.performance_ranker import PerformanceRanker
from quant_ecosystem.strategy_selector.regime_strategy_map import RegimeStrategyMap


class AutonomousStrategySelector:
    """Reads regime, ranks strategies, and applies activation decisions."""

    def __init__(
        self,
        strategy_bank_layer=None,
        strategy_engine=None,
        strategy_bank_engine=None,
        regime_source=None,
        ranker: Optional[PerformanceRanker] = None,
        regime_map: Optional[RegimeStrategyMap] = None,
        activation_manager: Optional[ActivationManager] = None,
        max_active_strategies: int = 5,
    ):
        self.strategy_bank_layer = strategy_bank_layer
        self.strategy_engine = strategy_engine
        self.strategy_bank_engine = strategy_bank_engine
        self.regime_source = regime_source
        self.ranker = ranker or PerformanceRanker()
        self.regime_map = regime_map or RegimeStrategyMap()
        self.activation_manager = activation_manager or ActivationManager(
            strategy_engine=strategy_engine,
            strategy_bank_engine=strategy_bank_engine,
            max_active_strategies=max_active_strategies,
        )
        self.max_active_strategies = max(1, int(max_active_strategies))

    def select(self, market_regime: str, risk_limits: Dict | None = None, capital_available_pct: float = 100.0) -> Dict:
        all_rows = self._strategy_rows()
        blocked_reasons: Dict[str, str] = {}
        rows: List[Dict] = []
        for row in all_rows:
            reason = self._tradeability_reason(row)
            sid = str(row.get("id", "")).strip() or "UNKNOWN"
            if reason:
                blocked_reasons[sid] = reason
            else:
                rows.append(row)

        if not rows:
            return {
                "regime": market_regime,
                "candidates": [],
                "selected": [],
                "activation": self.activation_manager.apply_selection([], available_ids=[]),
                "diagnostics": {
                    "total_rows": len(all_rows),
                    "tradeable_rows": 0,
                    "candidate_count": 0,
                    "selected_count": 0,
                    "blocked_reasons": blocked_reasons,
                },
            }

        filtered = [row for row in rows if self.regime_map.matches(row, market_regime)]
        filtered_ids = {str(row.get("id", "")).strip() for row in filtered if row.get("id")}
        for row in rows:
            sid = str(row.get("id", "")).strip()
            if sid and sid not in filtered_ids:
                blocked_reasons.setdefault(sid, "regime_mismatch")
        if not filtered:
            # Never fully empty selection from regime mapping alone.
            filtered = list(rows)
        ranked = self.ranker.rank(
            filtered,
            top_n=self.max_active_strategies,
            risk_limits=risk_limits or {},
            capital_available_pct=capital_available_pct,
        )
        if not ranked:
            ranked = self.ranker.rank(
                rows,
                top_n=max(1, self.max_active_strategies),
                risk_limits={"max_drawdown": 99.0, "min_profit_factor": 0.0, "min_sharpe": -99.0},
                capital_available_pct=capital_available_pct,
            )
        selected_ids = [row.get("id") for row in ranked if row.get("id")]
        if not selected_ids and rows:
            selected_ids = [str(rows[0].get("id"))] if rows[0].get("id") else []
        selected_set = {str(sid) for sid in selected_ids}
        for row in filtered:
            sid = str(row.get("id", "")).strip()
            if sid and sid not in selected_set:
                blocked_reasons.setdefault(sid, "not_selected_by_rank")
        activation = self.activation_manager.apply_selection(
            selected_ids=selected_ids,
            available_ids=[row.get("id") for row in rows],
        )
        return {
            "regime": market_regime,
            "candidates": filtered,
            "selected": ranked,
            "activation": activation,
            "diagnostics": {
                "total_rows": len(all_rows),
                "tradeable_rows": len(rows),
                "candidate_count": len(filtered),
                "selected_count": len(selected_ids),
                "blocked_reasons": blocked_reasons,
            },
        }

    def run_cycle(self, risk_limits: Dict | None = None, capital_available_pct: float = 100.0) -> Dict:
        regime = self._current_regime()
        return self.select(
            market_regime=regime,
            risk_limits=risk_limits,
            capital_available_pct=capital_available_pct,
        )

    def _current_regime(self) -> str:
        if callable(self.regime_source):
            try:
                value = self.regime_source()
                return str(value or "RANGE_BOUND").upper()
            except Exception:
                return "RANGE_BOUND"
        if isinstance(self.regime_source, dict):
            return str(self.regime_source.get("regime", "RANGE_BOUND")).upper()
        return "RANGE_BOUND"

    def _strategy_rows(self) -> List[Dict]:
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                rows = layer.registry_rows()
                if rows:
                    return rows
            except Exception:
                pass

        strategies = getattr(self.strategy_engine, "strategies", []) if self.strategy_engine else []
        out = []
        for row in strategies:
            out.append(
                {
                    "id": row.get("id"),
                    "category": row.get("category", "systematic"),
                    "sharpe": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "profit_factor": 0.0,
                    "allocation_pct": 0.0,
                }
            )
        return out

    def _tradeability_reason(self, row: Dict) -> str | None:
        strategy_id = str(row.get("id", "")).strip()
        if not strategy_id:
            return "missing_id"
        if strategy_id == "alpha_scanner_feed":
            return "non_deployable_feed"
        if bool(row.get("non_deployable", False)):
            return "non_deployable"
        if bool(row.get("diversity_blocked", False)):
            return "diversity_blocked"
        stage = str(row.get("stage", "")).upper()
        if stage in {"RESEARCH", "CANDIDATE", "BACKTESTED", "RETIRED", "REJECTED"}:
            return f"stage_{stage.lower()}"
        category = str(row.get("category", "")).strip().lower()
        if category in {"scanner", "scanner_feed"}:
            return "scanner_category"
        return None
