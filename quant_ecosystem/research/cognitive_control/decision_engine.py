"""High-level cognitive decision engine."""

from __future__ import annotations

from typing import Dict, Optional


class DecisionEngine:
    """Converts system state into high-level behavioral decisions."""

    def decide(self, state: Dict, memory_summary: Optional[Dict] = None) -> Dict:
        memory = dict(memory_summary or {})
        volatility = self._f(state.get("volatility_level", 0.0))
        drawdown = self._f(state.get("portfolio_drawdown", 0.0))
        latency_ms = self._f(state.get("execution_latency_ms", 0.0))
        pulse_events = int(state.get("pulse_events", 0) or 0)
        stress_events = int(memory.get("stress_events", 0) or 0)

        system_mode = "BALANCED"
        risk_level = "MEDIUM"
        strategy_type = "MIXED"
        actions = []

        if drawdown >= 15.0 or stress_events >= 5:
            system_mode = "DEFENSIVE"
            risk_level = "HIGH"
            strategy_type = "MEAN_REVERSION"
            actions.extend(["reduce_exposure", "pause_weak_strategies"])
        elif volatility >= 0.35 or pulse_events >= 5:
            system_mode = "CAUTIOUS"
            risk_level = "MEDIUM_HIGH"
            strategy_type = "VOLATILITY"
            actions.extend(["reduce_exposure"])
        elif volatility <= 0.14 and drawdown <= 2.0:
            system_mode = "AGGRESSIVE"
            risk_level = "LOW"
            strategy_type = "TREND"
            actions.extend(["increase_aggressiveness"])
        else:
            actions.extend(["hold"])

        if latency_ms > 600.0:
            actions.append("use_low_slippage_policy")

        return {
            "system_mode": system_mode,
            "portfolio_risk_level": risk_level,
            "preferred_strategy_type": strategy_type,
            "actions": actions,
            "inputs": {
                "volatility_level": round(volatility, 6),
                "portfolio_drawdown": round(drawdown, 6),
                "execution_latency_ms": round(latency_ms, 3),
                "pulse_events": pulse_events,
                "stress_events": stress_events,
            },
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

