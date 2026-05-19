from time import time
from typing import Any, Dict

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.profiles.base_profile import BaseProfile

from .discipline_governor import DisciplineAction, DisciplineDecision, DisciplineState


def evaluate_cooldown_manager(
    signal_intent: SignalIntent,
    profile: BaseProfile,
    state: DisciplineState,
) -> DisciplineDecision:
    if state.last_trade_at is None:
        return DisciplineDecision(
            action=DisciplineAction.ALLOW,
            reason="cooldown manager: no recent trade",
            confidence=0.30,
        )

    elapsed = time() - state.last_trade_at
    last_outcome = str(signal_intent.metadata.get("recent_outcome") or state.last_outcome).upper()
    if last_outcome == "LOSS":
        cooldown_seconds = profile.cooldown_after_loss_minutes * 60
    else:
        cooldown_seconds = profile.cooldown_after_win_minutes * 60

    if elapsed < cooldown_seconds:
        return DisciplineDecision(
            action=DisciplineAction.WAIT,
            reason=f"cooldown manager: waiting for profile cooldown ({int(cooldown_seconds - elapsed)}s remaining)",
            confidence=0.60,
            details={"remaining_seconds": int(cooldown_seconds - elapsed)},
        )

    return DisciplineDecision(
        action=DisciplineAction.ALLOW,
        reason="cooldown manager passed",
        confidence=0.30,
    )
