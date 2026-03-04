"""System-state API helpers for dashboard endpoints."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Callable, Deque, Dict, List, Optional


class SystemStateAPI:
    """Aggregates live router state into dashboard-friendly payloads."""
    _GLOBAL_EVENTS: Deque[Dict] = deque(maxlen=5000)

    def __init__(self, router_provider: Optional[Callable[[], object]] = None, max_events: int = 2000):
        self.router_provider = router_provider
        self._events: Deque[Dict] = deque(maxlen=max_events)

    def emit_event(self, event_type: str, payload: Optional[Dict] = None) -> Dict:
        event = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event_type": str(event_type),
            "payload": dict(payload or {}),
        }
        self._events.append(event)
        SystemStateAPI._GLOBAL_EVENTS.append(event)
        return event

    def get_events(self, limit: int = 200) -> List[Dict]:
        take = max(1, int(limit))
        merged = list(SystemStateAPI._GLOBAL_EVENTS)
        if not merged:
            merged = list(self._events)
        return merged[-take:]

    @classmethod
    def emit_global_event(cls, event_type: str, payload: Optional[Dict] = None) -> Dict:
        event = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event_type": str(event_type),
            "payload": dict(payload or {}),
        }
        cls._GLOBAL_EVENTS.append(event)
        return event

    def get_system_state(self) -> Dict:
        router = self._router()
        if not router:
            return {
                "online": False,
                "engines": {},
                "market": {},
                "portfolio": {},
                "events_queued": len(self._events),
            }

        state = getattr(router, "state", None)
        controller = getattr(router, "autonomous_controller", None)
        cc = getattr(router, "cognitive_controller", None)

        market = {
            "regime": str(getattr(controller, "last_regime", "UNKNOWN")),
            "volatility": self._f(getattr(getattr(router, "market_intelligence_layer", None), "last_volatility", 0.0)),
            "trend_direction": self._i(getattr(getattr(router, "market_intelligence_layer", None), "last_trend", 0)),
        }
        engines = {
            "market_pulse": self._engine_status(getattr(router, "market_pulse_engine", None)),
            "alpha_scanner": self._engine_status(getattr(router, "alpha_scanner", None)),
            "strategy_lab": self._engine_status(getattr(router, "strategy_lab_controller", None)),
            "meta_brain": self._engine_status(getattr(router, "meta_strategy_brain", None)),
            "adaptive_learning": self._engine_status(getattr(router, "adaptive_learning_engine", None)),
            "portfolio_ai": self._engine_status(getattr(router, "portfolio_ai_engine", None)),
            "execution_intelligence": self._engine_status(getattr(router, "execution_brain", None)),
            "broker": self._engine_status(getattr(getattr(router, "broker", None), "broker", None)),
            "cognitive_control": self._engine_status(cc),
        }
        if cc and getattr(cc, "last_decision", None):
            engines["cognitive_control"]["activity_level"] = len(
                (cc.last_decision.get("decision", {}) or {}).get("actions", [])
            )

        portfolio = {
            "equity": self._f(getattr(state, "equity", 0.0)),
            "cash": self._f(getattr(state, "cash_balance", 0.0)),
            "realized_pnl": self._f(getattr(state, "realized_pnl", 0.0)),
            "unrealized_pnl": self._f(getattr(state, "unrealized_pnl", 0.0)),
            "drawdown_pct": self._f(getattr(state, "total_drawdown_pct", 0.0)),
            "open_positions": len(getattr(getattr(router, "portfolio_engine", None), "positions", {}) or {}),
        }
        return {
            "online": True,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engines": engines,
            "market": market,
            "portfolio": portfolio,
            "events_queued": len(self._events),
        }

    def get_strategies(self) -> Dict:
        router = self._router()
        if not router:
            return {"active_strategies": [], "strategy_rows": []}
        active = list(getattr(getattr(router, "strategy_engine", None), "active_ids", []) or [])
        rows = []
        bank = getattr(router, "strategy_bank_engine", None)
        if bank and getattr(bank, "enabled", False):
            try:
                rows = bank.registry.all()
            except Exception:
                rows = []
        return {"active_strategies": active, "strategy_rows": rows}

    def get_portfolio(self) -> Dict:
        router = self._router()
        if not router:
            return {"positions": {}, "exposure_pct": 0.0}
        positions = getattr(getattr(router, "portfolio_engine", None), "positions", {}) or {}
        exposure = 0.0
        try:
            if hasattr(router, "_portfolio_exposure_pct"):
                exposure = self._f(router._portfolio_exposure_pct())
        except Exception:
            exposure = 0.0
        return {"positions": positions, "exposure_pct": exposure}

    def _engine_status(self, obj) -> Dict:
        if obj is None:
            return {"status": "OFF", "activity_level": 0, "last_event_ts": None}
        return {"status": "ON", "activity_level": 1, "last_event_ts": datetime.utcnow().strftime("%H:%M:%S")}

    def _router(self):
        if not self.router_provider:
            return None
        try:
            return self.router_provider()
        except Exception:
            return None

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _i(self, value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
