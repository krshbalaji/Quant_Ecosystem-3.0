from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.decision.decision_context import DecisionContext
from quant_ecosystem.decision.opportunity_classifier import OpportunityClassifier, OpportunityGrade
from quant_ecosystem.profiles import get_profile
from quant_ecosystem.risk.correlation_guard import CorrelationGuard
from quant_ecosystem.risk.reserve_manager import ReserveManager


class ArbitrationAction(str, Enum):
    TAKE = "TAKE"
    WAIT = "WAIT"
    REJECT = "REJECT"
    OVERRIDE = "OVERRIDE"


@dataclass
class ArbitrationDecision:
    action: ArbitrationAction
    reason: str
    selected_signal: Optional[SignalIntent] = None
    runner_up_signal: Optional[SignalIntent] = None
    details: Dict[str, Any] = None


PROFILE_PRIORITY: Dict[str, int] = {
    "SCALP": 6,
    "INTRADAY": 5,
    "FNO": 4,
    "SWING": 3,
    "MULTIBAGGER": 2,
    "INVESTMENT": 1,
}


class ArbitrationEngine:
    def __init__(self, classifier: Optional[OpportunityClassifier] = None):
        self.classifier = classifier or OpportunityClassifier()

    def _profile_for_signal(self, signal_intent: SignalIntent):
        profile_value = signal_intent.profile
        if isinstance(profile_value, ProfileTypes):
            return get_profile(profile_value)
        try:
            return get_profile(ProfileTypes(str(profile_value).upper()))
        except Exception:
            return get_profile(ProfileTypes.INTRADAY)

    def _score_signal(
        self,
        signal_intent: SignalIntent,
        discipline_decision: Any,
        market_regime: str,
    ) -> Tuple[OpportunityGrade, float]:
        profile = self._profile_for_signal(signal_intent)
        grade = self.classifier.classify(signal_intent, profile, discipline_decision, market_regime)
        priority = self.classifier.compute_priority(signal_intent, profile, grade, discipline_decision)
        priority += PROFILE_PRIORITY.get(str(profile.name).upper(), 0)

        regime_adjustment = self._regime_priority_adjustment(signal_intent, market_regime)
        if regime_adjustment.get("block"):
            return OpportunityGrade.C, 0.0

        priority += regime_adjustment.get("priority", 0.0)

        if str(market_regime).upper() == "HIGH_VOLATILITY":
            priority -= float(discipline_decision.confidence or 0.0) * 1.5

        return grade, max(0.0, priority)

    def _is_breakout_signal(self, signal_intent: SignalIntent) -> bool:
        pattern = str(signal_intent.metadata.get("signal_type", "") or signal_intent.metadata.get("pattern", "")).upper()
        if "BREAKOUT" in pattern or signal_intent.metadata.get("breakout"):
            return True
        return bool(str(signal_intent.metadata.get("strategy", "")).upper() in {"BREAKOUT", "MOMENTUM"})

    def _is_momentum_signal(self, signal_intent: SignalIntent) -> bool:
        if self._is_breakout_signal(signal_intent):
            return True
        if signal_intent.metadata.get("momentum"):
            return True
        return float(signal_intent.metadata.get("trend_strength", 0.0)) > 50.0

    def _is_aggressive_signal(self, signal_intent: SignalIntent) -> bool:
        if signal_intent.metadata.get("aggressive"):
            return True
        signal_type = str(signal_intent.metadata.get("signal_type", "")).upper()
        if signal_type in {"BREAKOUT", "MOMENTUM", "REVERSAL"}:
            return True
        risk_reward = float(signal_intent.metadata.get("risk_reward") or signal_intent.metadata.get("rr") or 0.0)
        return float(signal_intent.confidence or 0.0) >= 0.75 and risk_reward >= 1.8

    def _regime_priority_adjustment(self, signal_intent: SignalIntent, market_regime: str) -> Dict[str, Any]:
        regime = str(market_regime or "").upper()
        adjustment = {"priority": 0.0, "block": False}

        if regime == "TRENDING_BULL" and self._is_breakout_signal(signal_intent):
            adjustment["priority"] += 12.0
        elif regime == "RANGE_BOUND" and self._is_breakout_signal(signal_intent):
            adjustment["priority"] -= 10.0

        if regime == "CRASH_EVENT" and self._is_aggressive_signal(signal_intent):
            adjustment["block"] = True

        if regime == "TRENDING_BULL" and self._is_momentum_signal(signal_intent):
            adjustment["priority"] += 6.0

        return adjustment

    def _apply_correlation_guard(
        self,
        context: DecisionContext,
        candidate: SignalIntent,
    ) -> Tuple[bool, str]:
        if context.correlation_guard is None:
            return True, "correlation guard not installed"

        thesis = str(candidate.metadata.get("thesis") or candidate.symbol).upper()
        amount = float(candidate.metadata.get("notional", 0.0))
        group = str(candidate.metadata.get("correlation_group", "")).strip() or None

        allowed, reason = context.correlation_guard.evaluate(thesis, amount, group=group)
        if not allowed:
            return False, reason

        return True, reason

    def arbitrate(
        self,
        signals: List[SignalIntent],
        context: DecisionContext,
    ) -> ArbitrationDecision:
        if not signals:
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason="no signals provided",
                details={"signal_count": 0},
            )

        if str(context.risk_state).upper() == "RED":
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason="risk state RED prohibits execution",
                details={"risk_state": context.risk_state},
            )

        scored = []
        for signal in signals:
            grade, priority = self._score_signal(
                signal,
                context.discipline_decision,
                context.market_regime,
            )
            scored.append((signal, grade, priority))

        scored.sort(key=lambda item: (self.classifier.rank_value(item[1]), item[2]), reverse=True)
        best_signal, best_grade, best_priority = scored[0]
        runner_up = scored[1][0] if len(scored) > 1 else None
        runner_grade = scored[1][1] if len(scored) > 1 else None

        correlation_ok, correlation_reason = self._apply_correlation_guard(context, best_signal)
        if not correlation_ok:
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason=f"correlation guard: {correlation_reason}",
                selected_signal=best_signal,
                details={"grade": best_grade.value},
            )

        can_allocate = True
        can_allocate_reason = ""
        if context.capital_allocator is not None:
            amount = float(best_signal.metadata.get("notional", 0.0))
            if amount > 0.0:
                profile_name = self._profile_for_signal(best_signal).name
                can_allocate = context.capital_allocator.can_allocate(
                    profile_name,
                    amount,
                    allow_reserve=context.reserve_allowed,
                )
                if not can_allocate:
                    can_allocate_reason = "capital bucket unavailable"

        if best_grade == OpportunityGrade.A_PLUS and runner_up is not None:
            if context.reserve_manager is not None and context.reserve_manager.available > 0.0:
                return ArbitrationDecision(
                    action=ArbitrationAction.OVERRIDE,
                    reason="A+ opportunity may override weaker bucket usage",
                    selected_signal=best_signal,
                    runner_up_signal=runner_up,
                    details={
                        "best_grade": best_grade.value,
                        "runner_grade": runner_grade.value if runner_grade else None,
                        "reserve_available": context.reserve_manager.available,
                    },
                )

        if not can_allocate:
            return ArbitrationDecision(
                action=ArbitrationAction.WAIT,
                reason=f"cannot allocate capital: {can_allocate_reason}",
                selected_signal=best_signal,
                details={"requested_notional": best_signal.metadata.get("notional", 0.0)},
            )

        if context.portfolio_exposure_pct >= 80.0:
            return ArbitrationDecision(
                action=ArbitrationAction.WAIT,
                reason="portfolio exposure nearing limit",
                selected_signal=best_signal,
                details={"portfolio_exposure_pct": context.portfolio_exposure_pct},
            )

        if best_grade == OpportunityGrade.C:
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason="opportunity classified as C-grade",
                selected_signal=best_signal,
                details={"grade": best_grade.value},
            )

        return ArbitrationDecision(
            action=ArbitrationAction.TAKE,
            reason="selected highest-grade signal",
            selected_signal=best_signal,
            runner_up_signal=runner_up,
            details={
                "grade": best_grade.value,
                "priority": best_priority,
            },
        )
