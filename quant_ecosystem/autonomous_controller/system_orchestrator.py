"""Master orchestration coordinator for autonomous trading loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Optional

from quant_ecosystem.autonomous_controller.event_bus import BusEvent, EventBus
from quant_ecosystem.autonomous_controller.mode_manager import ControlMode, ModeManager


@dataclass
class OrchestratorHealth:
    cycle_count: int = 0
    last_cycle_at: str = ""
    last_error: str = ""
    last_regime: str = "RANGE_BOUND"
    last_trade_status: str = "IDLE"


class QuantOrchestrator:
    """Coordinates all engines required for one full trading cycle."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        mode_manager: Optional[ModeManager] = None,
        market_regime_engine=None,
        strategy_selector=None,
        strategy_bank_layer=None,
        capital_allocator=None,
        execution_router=None,
        risk_engine=None,
    ):
        self.event_bus = event_bus or EventBus()
        self.mode_manager = mode_manager or ModeManager(ControlMode.AUTONOMOUS)
        self.market_regime_engine = market_regime_engine
        self.strategy_selector = strategy_selector
        self.strategy_bank_layer = strategy_bank_layer
        self.capital_allocator = capital_allocator
        self.execution_router = execution_router
        self.risk_engine = risk_engine
        self.health = OrchestratorHealth()
        self._lock = RLock()
        self._last_selection: Dict[str, Any] = {}
        self._attach_default_subscribers()

    def read_market_data(self) -> Dict[str, Dict]:
        router = self.execution_router
        if not router:
            return {}
        symbols = list(getattr(router, "symbols", []) or [])
        if not symbols:
            symbols = ["NSE:NIFTY50-INDEX"]
        symbol = symbols[0]
        market_data = getattr(router, "market_data", None)
        if not market_data:
            return {}

        def frame(lookback: int, vol_base: float):
            close = market_data.get_close_series(symbol, lookback=lookback)
            if len(close) < 20:
                return {}
            high = [round(v * 1.0015, 6) for v in close]
            low = [round(v * 0.9985, 6) for v in close]
            return {
                "close": close,
                "high": high,
                "low": low,
                "volume": [vol_base + ((i % 7) * (vol_base * 0.02)) for i in range(len(close))],
                "spread": [0.05 if "NSE:" in symbol else 0.0002 for _ in close],
            }

        return {"5m": frame(80, 1000.0), "15m": frame(120, 1800.0), "1h": frame(160, 3000.0), "1d": frame(200, 5500.0)}

    def detect_regime(self, timeframe_data: Dict[str, Dict]) -> Dict:
        detector = self.market_regime_engine
        if not detector:
            return {"regime": "RANGE_BOUND", "confidence": 0.0, "details": {}}
        state = detector.detect_regime(timeframe_data=timeframe_data, extra_signals={})
        detector.broadcast_regime(
            state,
            strategy_bank_layer=self.strategy_bank_layer,
            autonomous_controller=self.mode_manager,
        )
        return state

    def select_strategies(self, regime: str) -> Dict:
        selector = self.strategy_selector
        if not selector:
            return {"selected": [], "activation": {"activated": [], "deactivated": [], "active_ids": []}}
        result = selector.select(
            market_regime=str(regime).upper(),
            risk_limits={"max_drawdown": 20.0, "min_profit_factor": 0.8, "min_sharpe": -5.0},
            capital_available_pct=100.0,
        )
        self._last_selection = result
        return result

    def allocate_capital(self, regime: str, current_drawdown_pct: float = 0.0) -> Dict:
        allocator = self.capital_allocator
        if not allocator:
            return {"allocation": {}, "rebalanced": False}
        rows = self._last_selection.get("selected") or self._strategy_rows()
        return allocator.rebalance(
            regime=str(regime).upper(),
            strategy_rows=rows,
            capital_available_pct=100.0,
            current_drawdown_pct=float(current_drawdown_pct),
        )

    def monitor_risk(self) -> Dict:
        router = self.execution_router
        if not router or not getattr(router, "state", None):
            return {"ok": True, "reason": "NO_STATE"}
        state = router.state
        drawdown = float(getattr(state, "total_drawdown_pct", 0.0))
        limit = float(getattr(self.risk_engine, "hard_drawdown_limit_pct", 20.0)) if self.risk_engine else 20.0
        if drawdown >= limit:
            self.event_bus.publish(BusEvent.RISK_ALERT, {"drawdown_pct": drawdown, "limit_pct": limit, "action": "HALT"})
            return {"ok": False, "reason": "MAX_DRAWDOWN_BREACH", "drawdown_pct": drawdown}
        return {"ok": True, "reason": "RISK_OK", "drawdown_pct": drawdown}

    def record_trade_event(self, trade_result: Dict) -> None:
        status = str(trade_result.get("status", "SKIP"))
        if status == "TRADE":
            self.event_bus.publish(BusEvent.TRADE_EXECUTED, trade_result)
        with self._lock:
            self.health.last_trade_status = status

    def mark_cycle(self, regime: str, error: str = "") -> None:
        with self._lock:
            self.health.cycle_count += 1
            self.health.last_cycle_at = datetime.now(timezone.utc).isoformat()
            self.health.last_regime = str(regime).upper()
            self.health.last_error = str(error or "")

    def health_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "cycle_count": self.health.cycle_count,
                "last_cycle_at": self.health.last_cycle_at,
                "last_error": self.health.last_error,
                "last_regime": self.health.last_regime,
                "last_trade_status": self.health.last_trade_status,
                "mode": self.mode_manager.get_mode(),
            }

    def _strategy_rows(self):
        layer = self.strategy_bank_layer
        if layer and hasattr(layer, "is_enabled") and layer.is_enabled():
            try:
                return list(layer.registry_rows())
            except Exception:
                return []
        return []

    def _attach_default_subscribers(self) -> None:
        self.event_bus.subscribe(BusEvent.RISK_ALERT, self._on_risk_alert)
        self.event_bus.subscribe(BusEvent.STRATEGY_ACTIVATED, self._noop_handler)
        self.event_bus.subscribe(BusEvent.STRATEGY_DEACTIVATED, self._noop_handler)
        self.event_bus.subscribe(BusEvent.REGIME_CHANGE, self._noop_handler)

    def _on_risk_alert(self, event: Dict[str, Any]) -> None:
        router = self.execution_router
        if not router:
            return
        payload = event.get("payload", {})
        if str(payload.get("action", "")).upper() == "HALT":
            try:
                router.stop_trading()
                router.set_auto_mode(False)
            except Exception:
                pass

    def _noop_handler(self, event: Dict[str, Any]) -> None:
        return

