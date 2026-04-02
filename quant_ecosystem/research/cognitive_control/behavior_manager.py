"""Behavior application layer for cognitive decisions."""

from __future__ import annotations

from typing import Dict


class BehaviorManager:
    """Applies high-level decisions to optional subsystem knobs."""

    def __init__(self, min_risk_pct: float = 0.5, max_risk_pct: float = 3.0, **kwargs):
        self.min_risk_pct = float(min_risk_pct)
        self.max_risk_pct = float(max_risk_pct)

    def apply(self, router, decision: Dict) -> Dict:
        actions = list(decision.get("actions", []) or [])
        applied = []

        risk_engine = getattr(router, "risk_engine", None)
        if risk_engine is not None and hasattr(risk_engine, "set_trade_risk_pct"):
            current = self._f(getattr(risk_engine, "max_trade_risk", 0.0))
            if "reduce_exposure" in actions:
                target = max(self.min_risk_pct, round(current * 0.9, 4))
                risk_engine.set_trade_risk_pct(target)
                applied.append({"risk_pct": target})
            elif "increase_aggressiveness" in actions:
                target = min(self.max_risk_pct, round(current * 1.05, 4))
                risk_engine.set_trade_risk_pct(target)
                applied.append({"risk_pct": target})

        if "pause_weak_strategies" in actions:
            try:
                survival = getattr(router, "strategy_survival_engine", None)
                if survival is not None:
                    setattr(survival, "prefer_retire", True)
                applied.append({"pause_weak_strategies": True})
            except Exception:
                pass

        if "use_low_slippage_policy" in actions:
            try:
                exec_brain = getattr(router, "execution_brain", None)
                if exec_brain is not None:
                    setattr(exec_brain, "forced_policy", "LOW_SLIPPAGE_MODE")
                    applied.append({"execution_policy": "LOW_SLIPPAGE_MODE"})
            except Exception:
                pass

        # Publish decision hints to optional modules as non-invasive metadata.
        for attr in ("portfolio_ai_engine", "meta_strategy_brain", "strategy_selector"):
            engine = getattr(router, attr, None)
            if engine is not None:
                try:
                    setattr(engine, "last_cognitive_decision", decision)
                except Exception:
                    pass

        return {"applied": applied, "action_count": len(actions)}

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

