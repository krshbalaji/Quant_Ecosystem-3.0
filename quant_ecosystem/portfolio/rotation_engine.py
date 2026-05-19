from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from quant_ecosystem.contracts.portfolio_decision import PortfolioDecision
from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.portfolio.portfolio_snapshot import PortfolioSnapshot
from quant_ecosystem.portfolio.position_health import HealthState, assess_position_health
from quant_ecosystem.portfolio.thesis_lifecycle import infer_lifecycle


PROFILE_PRIORITY: Dict[str, int] = {
    "SCALP": 6,
    "INTRADAY": 5,
    "FNO": 4,
    "SWING": 3,
    "MULTIBAGGER": 2,
    "INVESTMENT": 1,
}


def _normalize_profile(profile: Any) -> ProfileTypes:
    if isinstance(profile, ProfileTypes):
        return profile
    try:
        return ProfileTypes(str(profile).upper())
    except Exception:
        return ProfileTypes.INTRADAY


def _to_position(position: Any) -> Position:
    if isinstance(position, Position):
        return position
    if isinstance(position, dict):
        return Position.from_mapping(position)
    raise TypeError("position must be a Position or dict mapping")


def _to_signal(signal: Any) -> SignalIntent:
    if isinstance(signal, SignalIntent):
        return signal
    if isinstance(signal, dict):
        return SignalIntent.from_mapping(signal)
    raise TypeError("candidate signal must be a SignalIntent or dict mapping")


def _position_notional(position: Position) -> float:
    return abs(position.qty) * max(abs(position.avg_entry), 1.0)


def _position_strength(position: Position, trend_proxy: float = 0.0) -> float:
    trend = max(0.0, min(1.0, float(trend_proxy)))
    confidence = max(0.0, min(1.0, float(position.thesis.get("confidence", 0.0) or 0.0)))
    pnl_pct = float(position.pnl_unrealized) / max(1.0, _position_notional(position))
    health = assess_position_health(position, trend_proxy=trend)
    health_score = {
        HealthState.HEALTHY: 0.8,
        HealthState.BREAKOUT: 1.0,
        HealthState.HIGH_CONVICTION: 0.9,
        HealthState.RECOVERY: 0.55,
        HealthState.WEAK: 0.3,
        HealthState.DISTRIBUTION: 0.35,
        HealthState.EXIT_RISK: 0.1,
        HealthState.DEAD_MONEY: 0.05,
    }.get(health, 0.2)
    return max(0.0, min(1.0, (trend * 0.25) + (confidence * 0.25) + (max(-0.2, min(0.2, pnl_pct)) * 1.5) + (health_score * 0.35)))


def _candidate_strength(signal: SignalIntent) -> float:
    score = float(signal.metadata.get("score", 0.0) or 0.0)
    confidence = max(0.0, min(1.0, float(signal.confidence)))
    profile = _normalize_profile(signal.profile)
    profile_bonus = PROFILE_PRIORITY.get(profile.name, 0) / 10.0
    normalized_score = max(0.0, min(1.0, score / 100.0))
    return max(0.0, min(1.0, (normalized_score * 0.6) + (confidence * 0.3) + (profile_bonus * 0.1)))


class RotationEngine:
    def rank_existing_positions(
        self,
        snapshot: PortfolioSnapshot,
        trend_proxy_map: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[Position, float]]:
        ranked: List[Tuple[Position, float]] = []
        for position in snapshot.positions.values():
            proxy = float((trend_proxy_map or {}).get(position.symbol, position.metadata.get("trend_proxy", 0.0)) or 0.0)
            strength = _position_strength(position, trend_proxy=proxy)
            ranked.append((position, strength))
        return sorted(ranked, key=lambda item: item[1])

    def compare_opportunity(
        self,
        current_position: Any,
        candidate_signal: Any,
        trend_proxy: float = 0.0,
    ) -> Dict[str, Any]:
        position = _to_position(current_position)
        signal = _to_signal(candidate_signal)
        current_strength = _position_strength(position, trend_proxy=trend_proxy)
        candidate_strength = _candidate_strength(signal)
        profile_current = _normalize_profile(position.profile)
        profile_candidate = _normalize_profile(signal.profile)
        profile_advantage = PROFILE_PRIORITY.get(profile_candidate.name, 0) - PROFILE_PRIORITY.get(profile_current.name, 0)
        score_delta = candidate_strength - current_strength
        rotate_recommended = score_delta >= 0.20 or (candidate_strength >= 0.85 and current_strength <= 0.45)
        if profile_advantage > 0 and score_delta >= 0.10:
            rotate_recommended = True
        opportunity_cost = _position_notional(position) - float(signal.metadata.get("notional", 0.0) or 0.0)
        if opportunity_cost < 0:
            opportunity_cost = abs(opportunity_cost)
        return {
            "current_strength": round(current_strength, 3),
            "candidate_strength": round(candidate_strength, 3),
            "profile_current": profile_current.name,
            "profile_candidate": profile_candidate.name,
            "score_delta": round(score_delta, 3),
            "profile_advantage": profile_advantage,
            "opportunity_cost": round(opportunity_cost, 2),
            "rotate": rotate_recommended,
        }

    def recommend_rotation(
        self,
        snapshot: PortfolioSnapshot,
        candidates: Iterable[Union[SignalIntent, Dict[str, Any]]],
        trend_proxy_map: Optional[Dict[str, float]] = None,
    ) -> List[PortfolioDecision]:
        decisions: List[PortfolioDecision] = []
        ranked_positions = self.rank_existing_positions(snapshot, trend_proxy_map=trend_proxy_map)
        if not ranked_positions:
            return []
        candidates_list = [_to_signal(c) for c in candidates]
        if not candidates_list:
            return []

        weakest_position, weakest_strength = ranked_positions[0]
        trend_proxy = float((trend_proxy_map or {}).get(weakest_position.symbol, weakest_position.metadata.get("trend_proxy", 0.0)) or 0.0)
        for candidate in candidates_list:
            comparison = self.compare_opportunity(weakest_position, candidate, trend_proxy=trend_proxy)
            if comparison["rotate"]:
                reason = (
                    f"rotation recommended: weak holding {weakest_position.symbol} vs superior candidate {candidate.symbol}"
                )
                decisions.append(
                    PortfolioDecision(
                        action="ROTATE",
                        symbol=weakest_position.symbol,
                        confidence=max(0.5, min(1.0, comparison["candidate_strength"])),
                        reason=reason,
                        profile=weakest_position.profile,
                        metadata={
                            "current_strength": comparison["current_strength"],
                            "candidate_strength": comparison["candidate_strength"],
                            "profile_current": comparison["profile_current"],
                            "profile_candidate": comparison["profile_candidate"],
                            "score_delta": comparison["score_delta"],
                            "opportunity_cost": comparison["opportunity_cost"],
                            "candidate_symbol": candidate.symbol,
                            "candidate_notional": float(candidate.metadata.get("notional", 0.0) or 0.0),
                        },
                    )
                )
                break
        return decisions


_rotation_engine = RotationEngine()


def rank_existing_positions(
    snapshot: PortfolioSnapshot,
    trend_proxy_map: Optional[Dict[str, float]] = None,
) -> List[Tuple[Position, float]]:
    return _rotation_engine.rank_existing_positions(snapshot, trend_proxy_map=trend_proxy_map)


def compare_opportunity(
    current_position: Any,
    candidate_signal: Any,
    trend_proxy: float = 0.0,
) -> Dict[str, Any]:
    return _rotation_engine.compare_opportunity(current_position, candidate_signal, trend_proxy=trend_proxy)


def recommend_rotation(
    snapshot: PortfolioSnapshot,
    candidates: Iterable[Union[SignalIntent, Dict[str, Any]]],
    trend_proxy_map: Optional[Dict[str, float]] = None,
) -> List[PortfolioDecision]:
    return _rotation_engine.recommend_rotation(snapshot, candidates, trend_proxy_map=trend_proxy_map)
