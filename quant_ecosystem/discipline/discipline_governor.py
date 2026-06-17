from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.profiles.base_profile import BaseProfile


class DisciplineAction(str, Enum):
    ALLOW = "ALLOW"
    WAIT = "WAIT"
    REJECT = "REJECT"
    LOCK = "LOCK"


@dataclass
class DisciplineDecision:
    action: DisciplineAction
    reason: str
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DisciplineState:
    reporting_date: str = field(default_factory=lambda: date.today().isoformat())
    daily_trades: int = 0
    daily_loss_streak: int = 0
    budget_used: float = 0.0
    profile_lock_until: Dict[str, float] = field(default_factory=dict)
    last_trade_at: Optional[float] = None
    last_outcome: str = ""
    last_profile: str = ""

    def _utc_timestamp(self) -> float:
        return datetime.now(timezone.utc).timestamp()

    def reset_daily_if_needed(self) -> None:
        today = date.today().isoformat()
        if today != self.reporting_date:
            self.reporting_date = today
            self.daily_trades = 0
            self.daily_loss_streak = 0
            self.budget_used = 0.0

    def is_profile_locked(self, profile_name: str) -> bool:
        expiry = self.profile_lock_until.get(profile_name.upper())
        if expiry is None:
            return False
        if self._utc_timestamp() >= expiry:
            self.profile_lock_until.pop(profile_name.upper(), None)
            return False
        return True

    def lock_profile(self, profile_name: str, lock_seconds: int) -> None:
        self.profile_lock_until[profile_name.upper()] = self._utc_timestamp() + float(lock_seconds)

    def record_trade(self, profile_name: str, risk_amount: float = 0.0, outcome: str = "") -> None:
        self.reset_daily_if_needed()
        self.daily_trades += 1
        self.budget_used += abs(float(risk_amount) or 0.0)
        self.last_trade_at = self._utc_timestamp()
        self.last_outcome = str(outcome).upper()
        self.last_profile = profile_name.upper()
        if self.last_outcome == "LOSS":
            self.daily_loss_streak += 1
        elif self.last_outcome == "WIN":
            self.daily_loss_streak = 0


@dataclass
class DisciplineGovernor:
    def evaluate(
        self,
        signal_intent: SignalIntent,
        profile: BaseProfile,
        state: DisciplineState,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> DisciplineDecision:
        state.reset_daily_if_needed()

        regime = str(market_data.get("market_regime", "") if market_data else "").upper()
        transition_alert = bool(market_data.get("transition_alert") if market_data else False)
        transition_type = str(market_data.get("transition_type", "") if market_data else "").upper()

        if regime == "CRASH_EVENT":
            return DisciplineDecision(
                action=DisciplineAction.LOCK,
                reason="crash event defensive lock",
                confidence=0.98,
                details={"market_regime": regime},
            )

        if transition_alert and transition_type in {"TRENDING_TO_REVERSAL", "VOLATILITY_TRANSITION", "LOW_VOL_TO_HIGH_VOL"}:
            if signal_intent.confidence < 0.7 or (signal_intent.metadata or {}).get("aggressive"):
                return DisciplineDecision(
                    action=DisciplineAction.LOCK,
                    reason=f"transition caution lock ({transition_type})",
                    confidence=0.85,
                    details={
                        "transition_type": transition_type,
                        "transition_score": float((market_data or {}).get("transition_score", 0.0)),
                    },
                )

        if state.is_profile_locked(profile.name):
            return DisciplineDecision(
                action=DisciplineAction.LOCK,
                reason=f"profile {profile.name} locked after recent adverse outcome",
                confidence=0.95,
            )

        from .revenge_guard import evaluate_revenge_guard
        from .anti_chase import evaluate_anti_chase
        from .overtrade_guard import evaluate_overtrade_guard
        from .cooldown_manager import evaluate_cooldown_manager

        revenge = evaluate_revenge_guard(signal_intent, profile, state)
        if revenge.action != DisciplineAction.ALLOW:
            return revenge

        anti_chase = evaluate_anti_chase(signal_intent, profile, market_data)
        if anti_chase.action == DisciplineAction.REJECT:
            return anti_chase

        overtrade = evaluate_overtrade_guard(profile, state)
        if overtrade.action != DisciplineAction.ALLOW:
            return overtrade

        cooldown = evaluate_cooldown_manager(signal_intent, profile, state)
        if cooldown.action != DisciplineAction.ALLOW:
            return cooldown

        return DisciplineDecision(
            action=DisciplineAction.ALLOW,
            reason="discipline checks passed",
            confidence=0.45,
        )


def evaluate(
    signal_intent: SignalIntent,
    profile: BaseProfile,
    state: DisciplineState,
    market_data: Optional[Dict[str, Any]] = None,
) -> DisciplineDecision:
    return DisciplineGovernor().evaluate(signal_intent, profile, state, market_data)
