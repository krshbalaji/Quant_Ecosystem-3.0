from typing import Any, Dict

from quant_ecosystem.profiles.base_profile import BaseProfile

from .discipline_governor import DisciplineAction, DisciplineDecision, DisciplineState


DAILY_TRADE_LIMITS = {
    "SCALP": 3,
    "INTRADAY": 4,
    "SWING": 2,
    "FNO": 3,
    "MULTIBAGGER": 2,
    "INVESTMENT": 1,
}

LOSS_STREAK_LIMITS = {
    "SCALP": 2,
    "INTRADAY": 3,
    "SWING": 4,
    "FNO": 3,
    "MULTIBAGGER": 4,
    "INVESTMENT": 5,
}


def evaluate_overtrade_guard(
    profile: BaseProfile,
    state: DisciplineState,
) -> DisciplineDecision:
    profile_name = profile.name.upper()
    trade_limit = DAILY_TRADE_LIMITS.get(profile_name, 3)
    loss_limit = LOSS_STREAK_LIMITS.get(profile_name, 3)
    budget_threshold = float(profile.daily_risk_budget or 0.0)

    if state.daily_trades >= trade_limit:
        return DisciplineDecision(
            action=DisciplineAction.REJECT,
            reason=f"overtrade guard: daily trade limit exceeded for {profile.name}",
            confidence=0.94,
            details={"daily_trades": state.daily_trades, "trade_limit": trade_limit},
        )

    if state.daily_loss_streak >= loss_limit:
        return DisciplineDecision(
            action=DisciplineAction.REJECT,
            reason=f"overtrade guard: loss streak limit exceeded for {profile.name}",
            confidence=0.93,
            details={"daily_loss_streak": state.daily_loss_streak, "loss_limit": loss_limit},
        )

    if budget_threshold > 0 and state.budget_used >= budget_threshold:
        return DisciplineDecision(
            action=DisciplineAction.REJECT,
            reason="overtrade guard: profile daily risk budget exhausted",
            confidence=0.95,
            details={"budget_used": state.budget_used, "budget_threshold": budget_threshold},
        )

    if budget_threshold > 0 and state.budget_used >= budget_threshold * 0.8:
        return DisciplineDecision(
            action=DisciplineAction.WAIT,
            reason="overtrade guard: daily budget approaching exhaustion",
            confidence=0.55,
            details={"budget_used": state.budget_used, "budget_threshold": budget_threshold},
        )

    return DisciplineDecision(
        action=DisciplineAction.ALLOW,
        reason="overtrade guard passed",
        confidence=0.30,
    )
