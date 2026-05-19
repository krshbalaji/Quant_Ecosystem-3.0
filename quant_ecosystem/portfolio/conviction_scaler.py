from __future__ import annotations

from typing import Any, Dict, Optional

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.portfolio_decision import PortfolioDecision
from quant_ecosystem.portfolio.position_health import assess_position_health, HealthState


DEFAULT_SCALE_FACTORS: Dict[ProfileTypes, float] = {
    ProfileTypes.SCALP: 0.15,
    ProfileTypes.INTRADAY: 0.20,
    ProfileTypes.SWING: 0.35,
    ProfileTypes.FNO: 0.25,
    ProfileTypes.MULTIBAGGER: 0.20,
    ProfileTypes.INVESTMENT: 0.10,
}


class ConvictionScaler:
    def __init__(
        self,
        max_add_count: int = 2,
        profile_scale_factors: Optional[Dict[ProfileTypes, float]] = None,
        min_trend_proxy: float = 0.40,
    ) -> None:
        self.max_add_count = max(0, int(max_add_count))
        self.profile_scale_factors = profile_scale_factors or DEFAULT_SCALE_FACTORS
        self.min_trend_proxy = max(0.0, min(1.0, float(min_trend_proxy)))

    def _to_position(self, position: Any) -> Position:
        if isinstance(position, Position):
            return position
        if isinstance(position, dict):
            return Position.from_mapping(position)
        raise TypeError("position must be a Position or dict mapping")

    def _normalize_profile(self, profile: Any) -> ProfileTypes:
        if isinstance(profile, ProfileTypes):
            return profile
        try:
            return ProfileTypes(str(profile).upper())
        except Exception:
            return ProfileTypes.INTRADAY

    def _can_scale(self, position: Position, trend_proxy: float) -> bool:
        if position.qty == 0:
            return False
        if float(position.pnl_unrealized) <= 0.0:
            return False
        if not bool(position.thesis.get("intact", True)):
            return False
        add_count = int(position.metadata.get("add_count", 0) or 0)
        if add_count >= self.max_add_count:
            return False
        if trend_proxy < self.min_trend_proxy:
            return False

        health = assess_position_health(position, trend_proxy=trend_proxy)
        return health in {HealthState.BREAKOUT, HealthState.HEALTHY, HealthState.HIGH_CONVICTION}

    def _scale_factor(self, position: Position) -> float:
        profile = self._normalize_profile(position.profile)
        return float(self.profile_scale_factors.get(profile, 0.2))

    def recommend_action(
        self,
        position: Any,
        trend_proxy: float = 0.0,
    ) -> PortfolioDecision:
        position = self._to_position(position)
        trend_proxy = max(0.0, min(1.0, float(trend_proxy)))
        can_scale = self._can_scale(position, trend_proxy)
        action = "BUY_MORE" if can_scale else "HOLD"
        reason = (
            "conviction scaler: positive winner with intact thesis and continuation momentum"
            if can_scale
            else "conviction scaler: scaling not appropriate"
        )
        confidence = 0.65 if can_scale else 0.35
        scale_factor = self._scale_factor(position) if can_scale else 0.0

        return PortfolioDecision(
            action=action,
            symbol=position.symbol,
            confidence=confidence,
            reason=reason,
            profile=position.profile,
            metadata={
                "trend_proxy": trend_proxy,
                "pnl_unrealized": float(position.pnl_unrealized),
                "intact": bool(position.thesis.get("intact", True)),
                "add_count": int(position.metadata.get("add_count", 0) or 0),
                "max_add_count": self.max_add_count,
                "scale_factor": round(scale_factor, 3),
            },
        )
