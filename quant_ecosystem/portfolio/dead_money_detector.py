from __future__ import annotations

from typing import Any, Dict

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.portfolio_decision import PortfolioDecision
from quant_ecosystem.portfolio.position_health import HealthState, assess_position_health


class DeadMoneyDetector:
    def __init__(
        self,
        min_holding_days: float = 10.0,
        max_flat_pct: float = 0.03,
        max_trend_proxy: float = 0.30,
    ) -> None:
        self.min_holding_days = max(0.0, float(min_holding_days))
        self.max_flat_pct = max(0.0, min(1.0, float(max_flat_pct)))
        self.max_trend_proxy = max(0.0, min(1.0, float(max_trend_proxy)))

    def _to_position(self, position: Any) -> Position:
        if isinstance(position, Position):
            return position
        if isinstance(position, dict):
            return Position.from_mapping(position)
        raise TypeError("position must be a Position or dict mapping")

    def _pnl_pct(self, position: Position) -> float:
        notional = max(1.0, abs(position.qty) * max(abs(position.avg_entry), 1.0))
        return float(position.pnl_unrealized) / notional

    def detect(self, position: Any, trend_proxy: float = 0.0) -> bool:
        position = self._to_position(position)
        if position.qty == 0:
            return False

        holding_days = float(position.metadata.get("holding_days", 0.0) or 0.0)
        pnl_pct = abs(self._pnl_pct(position))
        trend_proxy = max(0.0, min(1.0, float(trend_proxy)))
        health = assess_position_health(position, trend_proxy=trend_proxy)

        if holding_days < self.min_holding_days:
            return False

        if pnl_pct <= self.max_flat_pct and trend_proxy <= self.max_trend_proxy:
            return True

        if health == HealthState.WEAK and holding_days >= self.min_holding_days and trend_proxy <= self.max_trend_proxy:
            return True

        return False

    def recommend_action(self, position: Any, trend_proxy: float = 0.0) -> PortfolioDecision:
        position = self._to_position(position)
        rotate = self.detect(position, trend_proxy=trend_proxy)
        action = "ROTATE" if rotate else "WAIT"
        reason = (
            "dead money detected: long holding, flat performance, low momentum"
            if rotate
            else "position does not meet dead money criteria"
        )
        return PortfolioDecision(
            action=action,
            symbol=position.symbol,
            confidence=0.5 if rotate else 0.2,
            reason=reason,
            profile=position.profile,
            metadata={
                "holding_days": float(position.metadata.get("holding_days", 0.0) or 0.0),
                "trend_proxy": float(trend_proxy),
                "pnl_unrealized": float(position.pnl_unrealized),
                "dead_money": rotate,
            },
        )
