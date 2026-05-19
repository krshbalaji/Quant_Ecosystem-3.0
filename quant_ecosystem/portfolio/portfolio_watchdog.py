from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Union

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.portfolio_decision import PortfolioDecision
from quant_ecosystem.portfolio.position_health import HealthState, assess_position_health
from quant_ecosystem.portfolio.portfolio_snapshot import PortfolioSnapshot
from quant_ecosystem.portfolio.thesis_lifecycle import LifecycleState, infer_lifecycle


class PortfolioWatchdog:
    def __init__(
        self,
        min_buy_trend: float = 0.35,
        rotation_window_days: float = 21.0,
    ) -> None:
        self.min_buy_trend = max(0.0, min(1.0, float(min_buy_trend)))
        self.rotation_window_days = max(0.0, float(rotation_window_days))

    def _to_position(self, position: Any) -> Position:
        if isinstance(position, Position):
            return position
        if isinstance(position, dict):
            return Position.from_mapping(position)
        raise TypeError("position must be a Position or dict mapping")

    def _compute_confidence(self, position: Position, trend_proxy: float, confidence_decay: float) -> float:
        thesis_confidence = float(position.thesis.get("confidence", 0.0) or 0.0)
        score = (trend_proxy * 0.5) + (thesis_confidence * 0.4)
        score -= min(1.0, max(0.0, float(confidence_decay))) * 0.3
        return max(0.0, min(1.0, score))

    def _format_reason(self, position: Position, health: HealthState, lifecycle: LifecycleState) -> str:
        return (
            f"portfolio watchdog: {health.value.lower().replace('_', ' ')} "
            f"state for {lifecycle.value.lower()} position"
        )

    def _apply_regime_transition_overrides(
        self,
        action: str,
        reason: str,
        confidence: float,
        position: Position,
        regime_state: Optional[Dict[str, Any]] = None,
        transition_state: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, str, float]:
        if transition_state is not None:
            transition_type = str(transition_state.get("transition_type", "NONE")).upper()
            if transition_type == "TRENDING_TO_REVERSAL":
                if action in {"HOLD", "BUY_MORE"}:
                    action = "PARTIAL_EXIT"
                    reason = "tightened exits on trending reversal"
                    confidence = min(confidence, 0.55)
            elif transition_type == "VOLATILITY_TRANSITION":
                if action in {"HOLD", "BUY_MORE"}:
                    action = "PARTIAL_EXIT"
                    reason = "partial protect during volatility transition"
                    confidence = min(confidence, 0.65)

        if regime_state is not None:
            regime = str(regime_state.get("regime", "UNKNOWN")).upper()
            if regime == "CRASH_EVENT":
                if action != "FULL_EXIT":
                    action = "PARTIAL_EXIT"
                    reason = "defensive posture during crash event"
                    confidence = min(confidence, 0.50)

        return action, reason, confidence

    def _choose_action(
        self,
        position: Position,
        health: HealthState,
        lifecycle: LifecycleState,
        trend_proxy: float,
    ) -> str:
        if health in {HealthState.EXIT_RISK, HealthState.DEAD_MONEY}:
            return "FULL_EXIT"

        if health == HealthState.DISTRIBUTION:
            return "PARTIAL_EXIT" if float(position.pnl_unrealized) >= 0.0 else "FULL_EXIT"

        if health in {HealthState.BREAKOUT, HealthState.HEALTHY, HealthState.HIGH_CONVICTION}:
            return "HOLD"

        if health == HealthState.RECOVERY:
            if trend_proxy >= self.min_buy_trend and bool(position.thesis.get("intact", True)):
                return "BUY_MORE"
            return "HOLD"

        if health == HealthState.WEAK:
            holding_days = float(position.metadata.get("holding_days", 0.0) or 0.0)
            notional_base = max(1.0, abs(int(position.qty)) * max(abs(float(position.avg_entry)), 1.0))
            pnl_pct = abs(float(position.pnl_unrealized)) / notional_base
            if pnl_pct <= 0.06 and holding_days >= self.rotation_window_days:
                return "ROTATE"
            return "WAIT"

        return "WAIT"

    def evaluate_position(
        self,
        position: Any,
        trend_proxy: Optional[float] = None,
        confidence_decay: float = 0.0,
        regime_state: Optional[Dict[str, Any]] = None,
        transition_state: Optional[Dict[str, Any]] = None,
    ) -> PortfolioDecision:
        position = self._to_position(position)
        if trend_proxy is None:
            trend_proxy = float(position.metadata.get("trend_proxy", 0.0) or 0.0)
        trend_proxy = max(0.0, min(1.0, float(trend_proxy)))

        lifecycle = infer_lifecycle(position)
        health = assess_position_health(position, trend_proxy=trend_proxy, confidence_decay=confidence_decay)
        action = self._choose_action(position, health, lifecycle, trend_proxy)
        confidence = self._compute_confidence(position, trend_proxy, confidence_decay)
        reason = self._format_reason(position, health, lifecycle)

        action, reason, confidence = self._apply_regime_transition_overrides(
            action,
            reason,
            confidence,
            position,
            regime_state=regime_state,
            transition_state=transition_state,
        )

        return PortfolioDecision(
            action=action,
            symbol=position.symbol,
            confidence=confidence,
            reason=reason,
            profile=position.profile,
            metadata={
                "health": health.value,
                "lifecycle": lifecycle.value,
                "trend_proxy": trend_proxy,
                "holding_days": float(position.metadata.get("holding_days", 0.0) or 0.0),
                "pnl_unrealized": float(position.pnl_unrealized),
                "regime": str(regime_state.get("regime", "UNKNOWN")).upper() if regime_state else "UNKNOWN",
                "transition_type": str(transition_state.get("transition_type", "NONE")).upper() if transition_state else "NONE",
            },
        )

    def recommend_action(
        self,
        position: Any,
        trend_proxy: Optional[float] = None,
        confidence_decay: float = 0.0,
        regime_state: Optional[Dict[str, Any]] = None,
        transition_state: Optional[Dict[str, Any]] = None,
    ) -> PortfolioDecision:
        return self.evaluate_position(
            position,
            trend_proxy=trend_proxy,
            confidence_decay=confidence_decay,
            regime_state=regime_state,
            transition_state=transition_state,
        )

    def evaluate_portfolio(
        self,
        positions: Iterable[Union[Position, Dict[str, Any]]],
        trend_proxy_map: Optional[Dict[str, float]] = None,
        confidence_decay: float = 0.0,
        regime_state_map: Optional[Dict[str, Dict[str, Any]]] = None,
        transition_state_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        snapshot = PortfolioSnapshot.from_positions(positions)
        decisions: List[PortfolioDecision] = []
        for position in snapshot.positions.values():
            proxy = trend_proxy_map.get(position.symbol, float(position.metadata.get("trend_proxy", 0.0))) if trend_proxy_map else float(position.metadata.get("trend_proxy", 0.0))
            decisions.append(
                self.evaluate_position(
                    position,
                    trend_proxy=proxy,
                    confidence_decay=confidence_decay,
                    regime_state=regime_state_map.get(position.symbol) if regime_state_map else None,
                    transition_state=transition_state_map.get(position.symbol) if transition_state_map else None,
                )
            )

        actions: Dict[str, int] = {}
        for decision in decisions:
            actions[decision.action] = actions.get(decision.action, 0) + 1

        return {
            "snapshot": snapshot.summary(trend_proxy_map=trend_proxy_map),
            "decisions": [decision.to_dict() for decision in decisions],
            "action_counts": actions,
            "position_count": len(decisions),
        }
