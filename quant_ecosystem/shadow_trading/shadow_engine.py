"""Shadow trading engine running in parallel with live market loop."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from quant_ecosystem.shadow_trading.promotion_evaluator import PromotionEvaluator
from quant_ecosystem.shadow_trading.shadow_execution import ShadowExecution
from quant_ecosystem.shadow_trading.shadow_performance_tracker import ShadowPerformanceTracker
from quant_ecosystem.shadow_trading.shadow_portfolio import ShadowPortfolio


class ShadowTradingEngine:
    """Manages shadow strategies, execution simulation, and promotion events."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        shadow_execution: Optional[ShadowExecution] = None,
        shadow_portfolio: Optional[ShadowPortfolio] = None,
        performance_tracker: Optional[ShadowPerformanceTracker] = None,
        promotion_evaluator: Optional[PromotionEvaluator] = None,
        max_signals_per_cycle: int = 3,
    ):
        self.shadow_execution = shadow_execution or ShadowExecution()
        self.shadow_portfolio = shadow_portfolio or ShadowPortfolio(initial_capital=initial_capital)
        self.performance_tracker = performance_tracker or ShadowPerformanceTracker()
        self.promotion_evaluator = promotion_evaluator or PromotionEvaluator()
        self.max_signals_per_cycle = max(1, int(max_signals_per_cycle))
        self.shadow_strategy_ids: set[str] = set()
        self.last_cycle: Dict = {}
        self.last_promotions: List[Dict] = []
        self.events: List[Dict] = []

    def register_shadow_strategies(self, strategy_rows: List[Dict]) -> int:
        for row in strategy_rows or []:
            sid = str(row.get("id", row.get("strategy_id", ""))).strip()
            if sid:
                self.shadow_strategy_ids.add(sid)
        return len(self.shadow_strategy_ids)

    def run_cycle(self, router, market_bias: str = "NEUTRAL", regime: str = "MEAN_REVERSION") -> Dict:
        if not getattr(router, "strategy_engine", None):
            return {"executed": 0, "promotions": []}
        snapshots = router._build_snapshots(regime=regime) if hasattr(router, "_build_snapshots") else []
        if not snapshots:
            return {"executed": 0, "promotions": []}

        candidates = router.strategy_engine.evaluate(
            snapshots=snapshots,
            market_bias=market_bias,
            regime=regime,
        ) or []
        if not candidates:
            return {"executed": 0, "promotions": []}

        # Favor explicit shadow candidates, then strongest candidates.
        candidates = sorted(candidates, key=lambda row: float(row.get("confidence", 0.0)), reverse=True)
        selected = []
        for cand in candidates:
            sid = str(cand.get("strategy_id", "")).strip()
            if sid and (sid in self.shadow_strategy_ids or bool(cand.get("shadow_mode", False))):
                selected.append(cand)
            if len(selected) >= self.max_signals_per_cycle:
                break
        if not selected:
            selected = candidates[: self.max_signals_per_cycle]

        trade_rows = []
        latest_prices = {}
        for snap in snapshots:
            sym = str(snap.get("symbol", ""))
            px = float(snap.get("price", 0.0) or 0.0)
            if sym and px > 0:
                latest_prices[sym] = px

        for sig in selected:
            signal = dict(sig)
            signal["qty"] = int(signal.get("qty", 1) or 1)
            signal["regime"] = regime
            fill = self.shadow_execution.simulate_fill(signal)
            mark = latest_prices.get(fill["symbol"], float(fill["entry_price"]))
            realized = self.shadow_portfolio.apply_fill(fill=fill, mark_price=mark)
            row = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "strategy_id": fill["strategy_id"],
                "symbol": fill["symbol"],
                "side": fill["side"],
                "qty": fill["qty"],
                "entry_price": fill["entry_price"],
                "exit_price": mark,
                "slippage_bps": fill["slippage_bps"],
                "fee": fill["fee"],
                "regime": fill["regime"],
                "pnl": float(realized.get("realized_pnl", 0.0)),
            }
            trade_rows.append(row)
            self.performance_tracker.record(row)
            self.events.append({"type": "SHADOW_EXECUTED", "payload": row})

        metrics = self.performance_tracker.all_metrics()
        promotions = self.promotion_evaluator.evaluate(metrics)
        self.last_promotions = promotions
        for evt in promotions:
            self.events.append({"type": "SHADOW_PROMOTION", "payload": evt})

        # Publish to integrated modules as hints.
        for attr in ("strategy_lab_controller", "meta_strategy_brain", "portfolio_ai_engine", "execution_brain", "adaptive_learning_engine"):
            target = getattr(router, attr, None)
            if target is not None:
                try:
                    setattr(target, "last_shadow_cycle", {"trades": trade_rows, "metrics": metrics, "promotions": promotions})
                except Exception:
                    pass

        self.last_cycle = {
            "executed": len(trade_rows),
            "promotions": promotions,
            "equity": round(self.shadow_portfolio.equity, 6),
            "exposure_pct": round(self.shadow_portfolio.exposure_pct(), 6),
        }
        return dict(self.last_cycle)



# ---------------------------------------------------------------------------
# SystemFactory-compatible alias
# ---------------------------------------------------------------------------

class ShadowEngine:
    """Minimal SystemFactory entry-point for shadow trading.

    Delegates to :class:`ShadowTradingEngine` when available.
    """

    def __init__(self) -> None:
        import logging as _logging
        self._log = _logging.getLogger(__name__)
        self._delegate = None
        try:
            self._delegate = ShadowTradingEngine()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("ShadowEngine: delegate unavailable (%s) — stub mode", exc)
        self._log.info("ShadowEngine initialized")

    def mirror_trades(self, signals: list, market_data: dict | None = None) -> list:
        """Simulate *signals* in the shadow portfolio.

        Returns a list of shadow execution result dicts.
        Falls back to empty list on error.
        """
        if self._delegate is not None:
            try:
                return self._delegate.process_signals(
                    signals=signals, market_data=market_data or {}
                )
            except Exception as exc:  # noqa: BLE001
                self._log.warning("ShadowEngine.mirror_trades: delegate error (%s)", exc)
        results = []
        for sig in signals:
            symbol = sig.get("symbol", "UNKNOWN") if isinstance(sig, dict) else str(sig)
            results.append({"symbol": symbol, "status": "shadow_skipped", "pnl": 0.0})
        return results
