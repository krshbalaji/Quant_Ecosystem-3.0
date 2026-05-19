from typing import Any, Dict, Optional

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.profiles.base_profile import BaseProfile

from .discipline_governor import DisciplineAction, DisciplineDecision


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def evaluate_anti_chase(
    signal_intent: SignalIntent,
    profile: BaseProfile,
    market_data: Optional[Dict[str, Any]] = None,
) -> DisciplineDecision:
    market = market_data or {}
    metadata = signal_intent.metadata or {}

    entry_price = _safe_float(metadata.get("entry_price") or metadata.get("price") or market.get("price"))
    current_price = _safe_float(market.get("price") or metadata.get("current_price") or entry_price)
    atr = _safe_float(metadata.get("atr") or market.get("atr"))
    risk_reward = _safe_float(metadata.get("risk_reward") or metadata.get("rr"))
    breakout_age = _safe_float(metadata.get("breakout_age_minutes") or metadata.get("breakout_age"))
    gap = abs(current_price - entry_price)

    if atr > 0 and gap > atr * 1.5:
        return DisciplineDecision(
            action=DisciplineAction.REJECT,
            reason="anti-chase: price extended beyond ATR threshold",
            confidence=0.95,
            details={"atr": atr, "price_gap": gap},
        )

    if breakout_age > 20:
        return DisciplineDecision(
            action=DisciplineAction.REJECT,
            reason="anti-chase: breakout appears exhausted",
            confidence=0.92,
            details={"breakout_age_minutes": breakout_age},
        )

    if 0 < risk_reward < 1.2:
        return DisciplineDecision(
            action=DisciplineAction.REJECT,
            reason="anti-chase: poor risk-reward ratio",
            confidence=0.90,
            details={"risk_reward": risk_reward},
        )

    return DisciplineDecision(
        action=DisciplineAction.ALLOW,
        reason="anti-chase passed",
        confidence=0.35,
    )
