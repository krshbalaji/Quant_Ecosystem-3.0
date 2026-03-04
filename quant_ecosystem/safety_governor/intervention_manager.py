"""Safety intervention execution manager."""

from __future__ import annotations

from typing import Dict, List


class InterventionManager:
    """Applies THROTTLE / RESTRICT / EMERGENCY_STOP responses."""

    LEVEL_PRIORITY = {"THROTTLE": 1, "RESTRICT": 2, "EMERGENCY_STOP": 3}

    def resolve_level(self, alerts: List[Dict]) -> str:
        if not alerts:
            return "NONE"
        return max(
            (str(item.get("level", "THROTTLE")).upper() for item in alerts),
            key=lambda lvl: self.LEVEL_PRIORITY.get(lvl, 0),
        )

    def apply(self, router, level: str, reason: str, alerts: List[Dict]) -> Dict:
        lvl = str(level or "NONE").upper()
        actions: List[str] = []
        if lvl == "NONE":
            return {"alert_level": "NONE", "reason": "No intervention", "actions": actions}

        risk_engine = getattr(router, "risk_engine", None)
        if lvl == "THROTTLE":
            if risk_engine and hasattr(risk_engine, "set_trade_risk_pct"):
                cur = self._f(getattr(risk_engine, "max_trade_risk", 0.0))
                new_val = risk_engine.set_trade_risk_pct(max(0.5, cur * 0.5))
                actions.append(f"Reduce trade risk to {round(new_val, 4)}%")
            setattr(router, "trade_size_multiplier", 0.5)
            actions.append("Reduce trade size multiplier to 0.5")

        elif lvl == "RESTRICT":
            if risk_engine and hasattr(risk_engine, "set_trade_risk_pct"):
                cur = self._f(getattr(risk_engine, "max_trade_risk", 0.0))
                new_val = risk_engine.set_trade_risk_pct(max(0.5, cur * 0.35))
                actions.append(f"Reduce trade risk to {round(new_val, 4)}%")
            setattr(router, "trade_size_multiplier", 0.35)
            if hasattr(router.state, "cooldown"):
                router.state.cooldown = max(int(getattr(router.state, "cooldown", 0)), 3)
                actions.append("Enforce execution cooldown (>=3 cycles)")
            strategy_engine = getattr(router, "strategy_engine", None)
            active_ids = list(getattr(strategy_engine, "active_ids", []) or [])
            if len(active_ids) > 1:
                strategy_engine.active_ids = active_ids[:1]
                actions.append(f"Pause strategies: keep only {strategy_engine.active_ids}")

        elif lvl == "EMERGENCY_STOP":
            try:
                router.kill_switch()
                actions.append("Kill switch activated")
            except Exception:
                pass
            # Attempt safe close of open positions.
            portfolio = getattr(router, "portfolio_engine", None)
            broker = getattr(router, "broker", None)
            positions = portfolio.snapshot() if portfolio and hasattr(portfolio, "snapshot") else {}
            closed = 0
            for symbol in list((positions or {}).keys()):
                try:
                    broker.close_position(symbol)
                    if portfolio and hasattr(portfolio, "positions"):
                        portfolio.positions.pop(symbol, None)
                    closed += 1
                except Exception:
                    continue
            actions.append(f"Close positions attempted: {closed}")

        # Broadcast summary to optional modules.
        for attr in ("cognitive_controller", "portfolio_ai_engine", "execution_brain"):
            engine = getattr(router, attr, None)
            if engine is not None:
                try:
                    setattr(engine, "last_safety_event", {"level": lvl, "reason": reason, "alerts": alerts})
                except Exception:
                    pass

        action_text = "; ".join(actions) if actions else "No action executed"
        return {
            "alert_level": lvl,
            "reason": reason,
            "action": action_text,
            "actions": actions,
            "alerts": alerts,
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

