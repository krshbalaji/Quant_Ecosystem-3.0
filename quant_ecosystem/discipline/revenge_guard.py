from time import time
from typing import Any, Dict

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.profiles.base_profile import BaseProfile

from .discipline_governor import DisciplineAction, DisciplineDecision, DisciplineState


PROFILE_LOCK_AFTER_LOSS = {
    "SCALP": 45 * 60,
    "INTRADAY": 30 * 60,
    "SWING": 120 * 60,
    "FNO": 45 * 60,
    "MULTIBAGGER": 180 * 60,
    "INVESTMENT": 240 * 60,
}


def evaluate_revenge_guard(
    signal_intent: SignalIntent,
    profile: BaseProfile,
    state: DisciplineState,
) -> DisciplineDecision:
    if state.is_profile_locked(profile.name):
        return DisciplineDecision(
            action=DisciplineAction.LOCK,
            reason=f"revenge guard: profile {profile.name} is locked",
            confidence=0.96,
            details={"locked_until": state.profile_lock_until.get(profile.name.upper())},
        )

    outcome = str(signal_intent.metadata.get("recent_outcome", "")).upper()
    if outcome == "LOSS":
        lock_seconds = PROFILE_LOCK_AFTER_LOSS.get(profile.name.upper(), 30 * 60)
        state.lock_profile(profile.name, lock_seconds)
        return DisciplineDecision(
            action=DisciplineAction.LOCK,
            reason=f"revenge guard: profile {profile.name} locked after stop loss",
            confidence=0.97,
            details={"lock_seconds": lock_seconds},
        )

    return DisciplineDecision(
        action=DisciplineAction.ALLOW,
        reason="revenge guard passed",
        confidence=0.32,
    )
