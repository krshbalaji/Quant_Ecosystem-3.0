"""Continuous autonomous trading loop (Phase D-12)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from threading import Event, RLock, Thread
from typing import Any, Dict, Optional

from quant_ecosystem.autonomous_controller.event_bus import BusEvent
from quant_ecosystem.autonomous_controller.mode_manager import ControlMode


class AutonomousTradingLoop:
    """Fault-tolerant threaded trading loop with 30-second default interval."""

    def __init__(self, orchestrator, loop_interval_sec: float = 30.0):
        self.orchestrator = orchestrator
        self.loop_interval_sec = max(1.0, float(loop_interval_sec))
        self._stop = Event()
        self._running = Event()
        self._thread: Optional[Thread] = None
        self._lock = RLock()

    def start_loop(self) -> str:
        with self._lock:
            if self._running.is_set():
                return "Trading loop already running."
            self._stop.clear()
            self.orchestrator.event_bus.start()
            self._thread = Thread(target=self._run_forever, daemon=True, name="autonomous-trading-loop")
            self._thread.start()
            self._running.set()
            return "Trading loop started."

    def stop_loop(self, timeout: float = 5.0) -> str:
        self._stop.set()
        thread = None
        with self._lock:
            thread = self._thread
        if thread:
            thread.join(timeout=timeout)
        self.orchestrator.event_bus.stop()
        self._running.clear()
        with self._lock:
            self._thread = None
        return "Trading loop stopped."

    def run_cycle(self) -> Dict[str, Any]:
        mode = self.orchestrator.mode_manager.get_mode()
        cycle = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "regime": "RANGE_BOUND",
            "selection": {},
            "allocation": {},
            "trade": {"status": "SKIP", "reason": "NOT_EXECUTED"},
            "risk": {},
        }

        try:
            market_data = self.orchestrator.read_market_data()
            self.orchestrator.event_bus.publish(BusEvent.MARKET_UPDATE, {"frames": list(market_data.keys())})

            regime_state = self.orchestrator.detect_regime(market_data)
            regime = str(regime_state.get("regime", "RANGE_BOUND")).upper()
            cycle["regime"] = regime
            self.orchestrator.event_bus.publish(BusEvent.REGIME_CHANGE, regime_state)

            selection = self.orchestrator.select_strategies(regime)
            cycle["selection"] = selection
            activation = selection.get("activation", {})
            for sid in activation.get("activated", []):
                self.orchestrator.event_bus.publish(BusEvent.STRATEGY_ACTIVATED, {"id": sid, "regime": regime})
            for sid in activation.get("deactivated", []):
                self.orchestrator.event_bus.publish(BusEvent.STRATEGY_DEACTIVATED, {"id": sid, "regime": regime})

            current_drawdown = 0.0
            router = self.orchestrator.execution_router
            if router and getattr(router, "state", None):
                current_drawdown = float(getattr(router.state, "total_drawdown_pct", 0.0))
            allocation = self.orchestrator.allocate_capital(regime=regime, current_drawdown_pct=current_drawdown)
            cycle["allocation"] = allocation

            if mode == ControlMode.MANUAL:
                cycle["trade"] = {"status": "SKIP", "reason": "MANUAL_MODE"}
            elif mode == ControlMode.ASSISTED:
                cycle["trade"] = {"status": "SKIP", "reason": "ASSISTED_MODE_RECOMMEND_ONLY"}
            else:
                trade = self._execute_trade_cycle(regime)
                cycle["trade"] = trade
                self.orchestrator.record_trade_event(trade)

            risk = self.orchestrator.monitor_risk()
            cycle["risk"] = risk
            error = "" if risk.get("ok", True) else str(risk.get("reason", "RISK_ALERT"))
            self.orchestrator.mark_cycle(regime=regime, error=error)
            return cycle
        except Exception as exc:
            cycle["trade"] = {"status": "SKIP", "reason": "CYCLE_EXCEPTION"}
            cycle["risk"] = {"ok": False, "reason": "LOOP_EXCEPTION"}
            self.orchestrator.mark_cycle(regime=cycle["regime"], error=str(exc))
            self.orchestrator.event_bus.publish(
                BusEvent.RISK_ALERT,
                {"action": "WARN", "reason": "LOOP_EXCEPTION", "error": str(exc)},
            )
            return cycle

    def _run_forever(self) -> None:
        while not self._stop.is_set():
            self.run_cycle()
            if self._stop.wait(self.loop_interval_sec):
                break

    def _execute_trade_cycle(self, regime: str) -> Dict[str, Any]:
        router = self.orchestrator.execution_router
        if not router:
            return {"status": "SKIP", "reason": "NO_ROUTER"}

        result = self._run_execute(router, regime)
        if isinstance(result, dict):
            return result
        return {"status": "SKIP", "reason": "INVALID_EXEC_RESULT"}

    def _run_execute(self, router, regime: str):
        execute_fn = getattr(router, "execute", None)
        if execute_fn is None:
            return {"status": "SKIP", "reason": "NO_EXECUTE_FUNCTION"}

        try:
            maybe_coro = execute_fn(signal=None, market_bias="NEUTRAL", regime=self._map_regime(regime))
            if asyncio.iscoroutine(maybe_coro):
                return asyncio.run(maybe_coro)
            return maybe_coro
        except RuntimeError:
            # Fallback for rare nested-loop contexts.
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(execute_fn(signal=None, market_bias="NEUTRAL", regime=self._map_regime(regime)))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    def _map_regime(self, regime: str) -> str:
        mapping = {
            "TRENDING_BULL": "TREND",
            "TRENDING_BEAR": "TREND",
            "RANGE_BOUND": "MEAN_REVERSION",
            "HIGH_VOLATILITY": "HIGH_VOLATILITY",
            "LOW_VOLATILITY": "LOW_VOLATILITY",
            "CRASH_EVENT": "CRISIS",
        }
        return mapping.get(str(regime).upper(), "MEAN_REVERSION")

