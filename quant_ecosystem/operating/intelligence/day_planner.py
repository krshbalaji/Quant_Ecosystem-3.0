from __future__ import annotations

from typing import Any, Dict, Iterable, List


class DayPlanner:
    """Builds the desk plan before and during session startup."""

    def __init__(self, config: Any = None, **kwargs) -> None:
        self.config = config

    def plan(
        self,
        symbols: Iterable[str],
        strategies: Iterable[str],
        capital_intelligence=None,
        market_view: Dict[str, Any] | None = None,
        event_view: Dict[str, Any] | None = None,
        performance_log: Dict[str, Dict] | None = None,
    ) -> Dict[str, Any]:
        market_view = dict(market_view or {})
        event_view = dict(event_view or {})
        performance_log = dict(performance_log or {})

        selected_symbols = list(symbols or [])[:8]
        strategy_ids = list(strategies or [])[:5]
        if not strategy_ids:
            strategy_ids = ["fallback_trend"]

        risk_level = "MEDIUM"
        if market_view.get("risk_mode") == "RISK_OFF" or str(event_view.get("impact", "LOW")).upper() == "HIGH":
            risk_level = "LOW"
        elif str(market_view.get("market_bias", "RANGE")).upper() == "BULL":
            risk_level = "HIGH"

        capital_allocation = {}
        base_capital = float(getattr(self.config, "capital", 100000.0) or 100000.0)
        for sid in strategy_ids:
            metrics = performance_log.get(sid, {})
            confidence = 0.65 if sid.startswith("fallback_") else 0.9
            if capital_intelligence and hasattr(capital_intelligence, "allocate_dynamic"):
                capital_allocation[sid] = capital_intelligence.allocate_dynamic(
                    strategy_id=sid,
                    base_capital=base_capital / max(len(strategy_ids), 1),
                    confidence=confidence,
                    regime=str(market_view.get("market_bias", "RANGE")).upper(),
                    strategy_metrics=metrics,
                )
            else:
                capital_allocation[sid] = round(base_capital / max(len(strategy_ids), 1), 2)

        return {
            "symbols": selected_symbols,
            "strategies": strategy_ids,
            "capital_allocation": capital_allocation,
            "risk_level": risk_level,
        }
