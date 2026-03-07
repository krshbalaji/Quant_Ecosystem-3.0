"""Centralized portfolio risk governor."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from quant_ecosystem.risk_engine.correlation_monitor import CorrelationMonitor
from quant_ecosystem.risk_engine.drawdown_guard import DrawdownGuard
from quant_ecosystem.risk_engine.exposure_limiter import ExposureLimiter


class PortfolioRiskManager:
    """Evaluates portfolio risk and triggers defensive actions."""

    def __init__(
        self,
        execution_router=None,
        capital_allocator=None,
        drawdown_guard: Optional[DrawdownGuard] = None,
        correlation_monitor: Optional[CorrelationMonitor] = None,
        exposure_limiter: Optional[ExposureLimiter] = None, **kwargs
    ):
        self.execution_router = execution_router
        self.capital_allocator = capital_allocator
        self.drawdown_guard = drawdown_guard or DrawdownGuard(
            portfolio_dd_limit_pct=20.0,
            strategy_dd_limit_pct=10.0,
        )
        self.correlation_monitor = correlation_monitor or CorrelationMonitor(threshold=0.75)
        self.exposure_limiter = exposure_limiter or ExposureLimiter(
            max_strategy_exposure_pct=25.0,
            max_asset_exposure_pct=30.0,
            total_leverage_limit=1.5,
        )

    def evaluate_portfolio_risk(self, correlation_matrix: Dict[str, Dict[str, float]] | None = None) -> Dict:
        router = self.execution_router
        if not router:
            return {"ok": True, "reason": "NO_ROUTER"}

        state = getattr(router, "state", None)
        if not state:
            return {"ok": True, "reason": "NO_STATE"}

        positions = self._position_rows(router)
        strategy_owner_map = dict(getattr(router, "_symbol_strategy_owner", {}) or {})
        drawdown_portfolio = self.drawdown_guard.evaluate_portfolio(state)
        drawdown_strategy = self.drawdown_guard.evaluate_strategies(getattr(state, "trade_history", []))
        correlation = self.correlation_monitor.evaluate(positions, correlation_matrix=correlation_matrix)
        exposure = self.exposure_limiter.evaluate(state, positions, strategy_owner_map=strategy_owner_map)

        return {
            "portfolio_drawdown": drawdown_portfolio,
            "strategy_drawdown": drawdown_strategy,
            "correlation": correlation,
            "exposure": exposure,
            "risk_breached": bool(
                drawdown_portfolio.get("breached")
                or correlation.get("breached")
                or exposure.get("breached")
                or any(item.get("breached") for item in drawdown_strategy.values())
            ),
        }

    def trigger_risk_action(self, risk_snapshot: Dict) -> Dict:
        """Apply defensive actions based on evaluated risk."""
        if not risk_snapshot.get("risk_breached", False):
            return {"action": "NONE", "details": "No risk breach."}

        router = self.execution_router
        actions = []

        # Portfolio DD breach is highest priority.
        if risk_snapshot.get("portfolio_drawdown", {}).get("breached", False):
            reduced = self._reduce_allocation(50.0)
            actions.append({"type": "PORTFOLIO_DD", "result": reduced})
            if router:
                try:
                    router.stop_trading()
                    router.set_auto_mode(False)
                    actions.append({"type": "PAUSE", "result": "Trading paused due to portfolio drawdown breach."})
                except Exception as exc:
                    actions.append({"type": "PAUSE", "result": f"pause_failed:{exc}"})

        strategy_dd = risk_snapshot.get("strategy_drawdown", {})
        for sid, data in strategy_dd.items():
            if not data.get("breached", False):
                continue
            reduced = self._reduce_strategy_allocation(sid, 35.0)
            actions.append({"type": "STRATEGY_DD", "strategy_id": sid, "result": reduced})

        if risk_snapshot.get("correlation", {}).get("breached", False):
            reduced = self._reduce_allocation(20.0)
            actions.append({"type": "CORRELATION", "result": reduced})

        if risk_snapshot.get("exposure", {}).get("breached", False):
            reduced = self._reduce_allocation(25.0)
            actions.append({"type": "EXPOSURE", "result": reduced})

        if not actions:
            return {"action": "NONE", "details": "Breach detected but no actionable path."}
        return {"action": "RISK_ACTIONS_APPLIED", "actions": actions}

    def emergency_shutdown(self, reason: str = "MANUAL_EMERGENCY") -> Dict:
        """Immediate kill-switch + close all + deep exposure cut."""
        router = self.execution_router
        actions = {"reason": reason, "killed": False, "closed": [], "allocation_reduction": {}}
        if not router:
            return actions

        try:
            router.kill_switch()
            actions["killed"] = True
        except Exception:
            actions["killed"] = False

        # Try close all open positions.
        positions = self._position_rows(router)
        closed = []
        for row in positions:
            symbol = str(row.get("symbol", "")).strip()
            if not symbol:
                continue
            try:
                router.broker.close_position(symbol)
                closed.append(symbol)
            except Exception:
                continue
        actions["closed"] = closed
        actions["allocation_reduction"] = self._reduce_allocation(100.0)
        return actions

    def _position_rows(self, router) -> Iterable[Dict]:
        portfolio = getattr(router, "portfolio_engine", None)
        state = getattr(router, "state", None)
        prices = dict(getattr(state, "latest_prices", {}) or {})
        positions = []
        if not portfolio:
            return positions
        snapshot = portfolio.snapshot()
        for symbol, row in (snapshot or {}).items():
            net_qty = float(row.get("net_qty", 0.0))
            px = float(prices.get(symbol, row.get("avg_price", 0.0)))
            positions.append(
                {
                    "symbol": symbol,
                    "net_qty": net_qty,
                    "avg_price": float(row.get("avg_price", 0.0)),
                    "notional": abs(net_qty * px),
                }
            )
        return positions

    def _reduce_allocation(self, reduction_pct: float) -> Dict:
        allocator = self.capital_allocator
        if not allocator or not hasattr(allocator, "reduce_exposure"):
            return {"status": "NO_ALLOCATOR"}
        try:
            return allocator.reduce_exposure(reduction_pct=float(reduction_pct))
        except Exception as exc:
            return {"status": f"FAILED:{exc}"}

    def _reduce_strategy_allocation(self, strategy_id: str, reduction_pct: float) -> Dict:
        allocator = self.capital_allocator
        if not allocator:
            return {"status": "NO_ALLOCATOR"}

        current = dict(getattr(allocator, "last_allocation", {}) or {})
        sid = str(strategy_id).strip()
        if sid not in current:
            return {"status": "NOT_FOUND", "strategy_id": sid}
        factor = max(0.0, 1.0 - (float(reduction_pct) / 100.0))
        current[sid] = round(float(current[sid]) * factor, 4)
        allocator.last_allocation = current
        if hasattr(allocator, "_publish_to_bank"):
            try:
                allocator._publish_to_bank(current)
            except Exception:
                pass
        return {"strategy_id": sid, "allocation_pct": current[sid]}

