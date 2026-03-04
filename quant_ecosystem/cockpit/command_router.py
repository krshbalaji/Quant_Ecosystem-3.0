"""Routes cockpit commands to runtime modules."""

from __future__ import annotations

from typing import Dict, Optional


class CockpitCommandRouter:
    """Command router for Trading Cockpit actions."""

    def __init__(self, router_provider):
        self.router_provider = router_provider

    def execute(self, command: str, payload: Optional[Dict] = None) -> Dict:
        router = self.router_provider() if self.router_provider else None
        if router is None:
            return {"ok": False, "error": "router_unavailable"}
        cmd = str(command or "").strip().upper()
        body = dict(payload or {})

        try:
            if cmd == "START_TRADING":
                return {"ok": True, "result": router.start_trading()}
            if cmd == "PAUSE_TRADING":
                return {"ok": True, "result": router.stop_trading()}
            if cmd == "EMERGENCY_STOP":
                return {"ok": True, "result": router.kill_switch()}
            if cmd == "RESTART_ENGINES":
                return {"ok": True, "result": "Restart command accepted (soft restart not implemented)."}

            if cmd == "SET_RISK_LEVEL":
                level = float(body.get("risk_pct", 0.0))
                value = router.risk_engine.set_trade_risk_pct(level)
                return {"ok": True, "risk_pct": value}
            if cmd == "SET_MAX_DRAWDOWN":
                value = float(body.get("max_drawdown_pct", 20.0))
                setattr(router.risk_engine, "hard_drawdown_limit_pct", value)
                return {"ok": True, "max_drawdown_pct": value}
            if cmd == "SET_TRADE_SIZE_MULTIPLIER":
                mul = float(body.get("multiplier", 1.0))
                setattr(router, "trade_size_multiplier", mul)
                return {"ok": True, "trade_size_multiplier": mul}

            if cmd == "ACTIVATE_STRATEGY":
                sid = str(body.get("strategy_id", "")).strip()
                return {"ok": True, "result": self._activate_strategy(router, sid)}
            if cmd == "PAUSE_STRATEGY":
                sid = str(body.get("strategy_id", "")).strip()
                return {"ok": True, "result": self._pause_strategy(router, sid)}
            if cmd == "RETIRE_STRATEGY":
                sid = str(body.get("strategy_id", "")).strip()
                return {"ok": True, "result": self._retire_strategy(router, sid)}
            if cmd == "ADJUST_ALLOCATION":
                sid = str(body.get("strategy_id", "")).strip()
                pct = float(body.get("allocation_pct", 0.0))
                return {"ok": True, "result": self._adjust_allocation(router, sid, pct)}

            if cmd == "FORCE_REBALANCE":
                pai = getattr(router, "portfolio_ai_engine", None)
                if pai is None:
                    return {"ok": False, "error": "portfolio_ai_unavailable"}
                regime = str(getattr(router.autonomous_controller, "last_regime", "RANGE_BOUND")).upper()
                out = pai.run_cycle(regime=regime, capital_pct=100.0)
                return {"ok": True, "result": out}
            if cmd == "REDUCE_EXPOSURE":
                curr = float(getattr(router.risk_engine, "max_trade_risk", 1.0))
                tgt = router.risk_engine.set_trade_risk_pct(max(0.5, curr * 0.8))
                return {"ok": True, "risk_pct": tgt}
            if cmd == "CLOSE_ALL_POSITIONS":
                return {"ok": True, "result": self._close_all(router)}

            if cmd == "SET_EXECUTION_MODE":
                mode = str(body.get("mode", "LOW_SLIPPAGE_MODE")).upper()
                brain = getattr(router, "execution_brain", None)
                if brain is None:
                    return {"ok": False, "error": "execution_brain_unavailable"}
                setattr(brain, "forced_policy", mode)
                return {"ok": True, "execution_mode": mode}
            if cmd == "SET_SLIPPAGE_LIMIT":
                bps = float(body.get("slippage_bps", 0.0))
                setattr(router, "max_slippage_bps_override", bps)
                return {"ok": True, "slippage_bps": bps}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        return {"ok": False, "error": f"unknown_command:{cmd}"}

    def _activate_strategy(self, router, strategy_id: str) -> str:
        if not strategy_id:
            return "missing_strategy_id"
        selector = getattr(router, "strategy_selector", None)
        if selector and hasattr(selector, "activation_manager"):
            rows = []
            layer = getattr(router, "strategy_bank_layer", None)
            if layer and hasattr(layer, "registry_rows"):
                rows = layer.registry_rows()
            available_ids = [str(row.get("id")) for row in rows if row.get("id")]
            active = list(getattr(router.strategy_engine, "active_ids", []) or [])
            if strategy_id not in active:
                active.append(strategy_id)
            selector.activation_manager.apply_selection(selected_ids=active, available_ids=available_ids)
        return f"activated:{strategy_id}"

    def _pause_strategy(self, router, strategy_id: str) -> str:
        if not strategy_id:
            return "missing_strategy_id"
        active = set(getattr(router.strategy_engine, "active_ids", []) or [])
        if strategy_id in active:
            active.remove(strategy_id)
            router.strategy_engine.active_ids = list(active)
        return f"paused:{strategy_id}"

    def _retire_strategy(self, router, strategy_id: str) -> str:
        if not strategy_id:
            return "missing_strategy_id"
        bank = getattr(router, "strategy_bank_engine", None)
        if bank and hasattr(bank, "set_stage"):
            bank.set_stage(strategy_id, "RETIRED", reason="cockpit_command")
        self._pause_strategy(router, strategy_id)
        return f"retired:{strategy_id}"

    def _adjust_allocation(self, router, strategy_id: str, pct: float) -> str:
        if not strategy_id:
            return "missing_strategy_id"
        bank = getattr(router, "strategy_bank_engine", None)
        if not bank:
            return "strategy_bank_unavailable"
        if hasattr(bank, "set_allocation"):
            bank.set_allocation(strategy_id, pct)
        return f"allocation_set:{strategy_id}={pct}"

    def _close_all(self, router) -> str:
        positions = router.portfolio_engine.snapshot()
        if not positions:
            return "no_open_positions"
        closed = []
        for symbol in list(positions.keys()):
            try:
                router.broker.close_position(symbol)
                router.portfolio_engine.positions.pop(symbol, None)
                closed.append(symbol)
            except Exception:
                continue
        return f"closed:{len(closed)}"

