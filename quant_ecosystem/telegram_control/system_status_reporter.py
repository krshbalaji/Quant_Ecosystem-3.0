"""System status and health diagnostics formatter for Telegram control center."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict


class SystemStatusReporter:
    """Builds operational status and diagnostics snapshots."""

    def __init__(self, router=None, orchestrator=None, risk_manager=None):
        self.router = router
        self.orchestrator = orchestrator
        self.risk_manager = risk_manager

    def status_snapshot(self) -> str:
        router = self.router
        if not router:
            return "Status unavailable: router not attached."

        state = getattr(router, "state", None)
        strategy_engine = getattr(router, "strategy_engine", None)
        bank = getattr(router, "strategy_bank_engine", None)
        controller = getattr(router, "autonomous_controller", None)

        active = []
        if strategy_engine:
            active = sorted(list(getattr(strategy_engine, "active_ids", set()) or []))

        regime = str(getattr(controller, "last_regime", "UNKNOWN")) if controller else "UNKNOWN"
        mode = str(getattr(controller, "mode", "UNKNOWN")) if controller else "UNKNOWN"
        equity = float(getattr(state, "equity", 0.0)) if state else 0.0
        health = "OK"
        if state and (getattr(state, "trading_halted", False) or not getattr(state, "trading_enabled", True)):
            health = "PAUSED/HALTED"

        allocation = {}
        if bank and getattr(bank, "enabled", False):
            for sid in active:
                allocation[sid] = bank.get_allocation(sid)

        return (
            f"System Status\n"
            f"Mode: {mode}\n"
            f"Regime: {regime}\n"
            f"Health: {health}\n"
            f"Portfolio Value: {round(equity, 2)}\n"
            f"Active Strategies: {', '.join(active) if active else 'none'}\n"
            f"Allocations: {allocation if allocation else '{}'}"
        )

    def system_health(self) -> str:
        router = self.router
        if not router:
            return "System health unavailable: router not attached."

        ping_ms = self._latency_probe_ms()
        api = self._api_connectivity(router)
        risk_state = self._risk_state()
        orchestrator = self._orchestrator_health()

        return (
            f"System Health\n"
            f"Latency(ms): {ping_ms}\n"
            f"API Connectivity: {api}\n"
            f"Risk State: {risk_state}\n"
            f"Orchestrator: {orchestrator}"
        )

    def _latency_probe_ms(self) -> float:
        start = perf_counter()
        _ = datetime.now(timezone.utc).isoformat()
        end = perf_counter()
        return round((end - start) * 1000.0, 3)

    def _api_connectivity(self, router) -> str:
        broker_router = getattr(router, "broker", None)
        broker = getattr(broker_router, "broker", None) if broker_router else None
        if not broker:
            return "NO_BROKER"
        connected = bool(getattr(broker, "connected", False))
        source = str(getattr(router.state, "account_source", "UNKNOWN"))
        return f"connected={connected} source={source}"

    def _risk_state(self) -> str:
        manager = self.risk_manager
        if not manager:
            return "NO_RISK_MANAGER"
        try:
            snap = manager.evaluate_portfolio_risk()
            return "BREACHED" if snap.get("risk_breached", False) else "OK"
        except Exception as exc:
            return f"ERROR:{exc}"

    def _orchestrator_health(self) -> Dict[str, Any]:
        orch = self.orchestrator
        if not orch or not hasattr(orch, "health_snapshot"):
            return {"status": "NO_ORCHESTRATOR"}
        try:
            return orch.health_snapshot()
        except Exception as exc:
            return {"status": f"ERROR:{exc}"}

