from __future__ import annotations

from typing import Any, Dict

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.portfolio_decision import PortfolioDecision
from quant_ecosystem.portfolio.position_health import assess_position_health, HealthState


class ProfitProtector:
    def __init__(
        self,
        breakeven_pct: float = 0.01,
        partial_book_pct: float = 0.08,
        trail_threshold_pct: float = 0.05,
        lock_gain_pct: float = 0.15,
    ) -> None:
        self.breakeven_pct = max(0.0, float(breakeven_pct))
        self.partial_book_pct = max(0.0, float(partial_book_pct))
        self.trail_threshold_pct = max(0.0, float(trail_threshold_pct))
        self.lock_gain_pct = max(0.0, float(lock_gain_pct))

    def _to_position(self, position: Any) -> Position:
        if isinstance(position, Position):
            return position
        if isinstance(position, dict):
            return Position.from_mapping(position)
        raise TypeError("position must be a Position or dict mapping")

    def _pnl_pct(self, position: Position) -> float:
        notional = max(1.0, abs(position.qty) * max(abs(position.avg_entry), 1.0))
        return float(position.pnl_unrealized) / notional

    def recommend_action(self, position: Any, trend_proxy: float = 0.0) -> PortfolioDecision:
        position = self._to_position(position)
        pnl_pct = self._pnl_pct(position)
        health = assess_position_health(position, trend_proxy=trend_proxy)
        action = "HOLD"
        reason = "profit protector: no protective action required"
        confidence = 0.3

        if pnl_pct <= 0.0:
            return PortfolioDecision(
                action="WAIT",
                symbol=position.symbol,
                confidence=0.2,
                reason="profit protector: position not profitable",
                profile=position.profile,
                metadata={"pnl_pct": pnl_pct},
            )

        if pnl_pct >= self.lock_gain_pct:
            action = "HOLD"
            reason = "profit protector: strong gains, maintain position and tighten trail"
            confidence = 0.8
        elif pnl_pct >= self.partial_book_pct:
            action = "PARTIAL_EXIT"
            reason = "profit protector: positive winner meets partial booking threshold"
            confidence = 0.75
        elif pnl_pct >= self.breakeven_pct:
            action = "HOLD"
            reason = "profit protector: position above breakeven, ready for tighter risk management"
            confidence = 0.6

        if health == HealthState.DISTRIBUTION and pnl_pct >= self.partial_book_pct:
            action = "PARTIAL_EXIT"
            reason = "profit protector: distribution detected with available profit"
            confidence = 0.85

        return PortfolioDecision(
            action=action,
            symbol=position.symbol,
            confidence=confidence,
            reason=reason,
            profile=position.profile,
            metadata={
                "pnl_pct": pnl_pct,
                "trend_proxy": float(trend_proxy),
                "health": health.value,
                "lock_gain_pct": self.lock_gain_pct,
                "partial_book_pct": self.partial_book_pct,
            },
        )
