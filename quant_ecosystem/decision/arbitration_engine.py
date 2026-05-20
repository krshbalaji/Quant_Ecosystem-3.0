from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, List

from quant_ecosystem.decision.opportunity_classifier import (
    OpportunityClassifier,
    OpportunityGrade,
)
from quant_ecosystem.decision.decision_context import DecisionContext


class ArbitrationAction(str, Enum):
    TAKE = "TAKE"
    WAIT = "WAIT"
    REJECT = "REJECT"
    OVERRIDE = "OVERRIDE"


@dataclass
class ArbitrationDecision:
    action: ArbitrationAction
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    selected_signal: Optional[Any] = None


class ArbitrationEngine:
    """
    QE3 legacy + organism compatible arbitration engine
    """

    def __init__(self) -> None:
        self.classifier = OpportunityClassifier()

    def arbitrate(
        self,
        signal_candidates: List[Any],
        context: DecisionContext,
    ) -> ArbitrationDecision:
        if not signal_candidates:
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason="no signal candidates",
            )

        correlation_decision = self._check_correlation_guard(
            signal_candidates,
            context,
        )
        if correlation_decision:
            return correlation_decision

        best_signal = self._select_best_signal(signal_candidates)
        context.signal_intent = best_signal

        weak_decision = self._check_regime_memory_performance(
            best_signal,
            context,
        )
        if weak_decision:
            return weak_decision

        decision = self.evaluate(context)
        decision.selected_signal = best_signal

        if len(signal_candidates) > 1:
            if best_signal is not signal_candidates[0]:
                if decision.action in {
                    ArbitrationAction.TAKE,
                    ArbitrationAction.WAIT,
                }:
                    decision.action = ArbitrationAction.OVERRIDE
                    decision.reason = "best candidate selected"

        return decision

    def evaluate(
        self,
        context: DecisionContext,
    ) -> ArbitrationDecision:
        signal = context.signal_intent

        if signal is None:
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason="missing signal",
            )

        weak_decision = self._check_regime_memory_performance(
            signal,
            context,
        )
        if weak_decision:
            return weak_decision
            
        regime = str(
            getattr(context, "market_regime", None) or "RANGE_BOUND"
        ).upper()

        profile = getattr(context, "profile", None)

        assessment = self.classifier.classify(
            signal_intent=signal,
            market_regime=regime,
            profile=profile,
        )

        adjusted_score = float(assessment.effective_score)

        adjustment = self._regime_priority_adjustment(signal, regime)
        adjusted_score += adjustment["priority"]

        regime_conf = self._extract_regime_confidence(context)

        if regime_conf < 0.45:
            adjusted_score -= 3.0

        if self._high_confidence_signal(signal):
            adjusted_score += 3.0

        metadata = getattr(signal, "metadata", {}) or {}

        strategy_winrate = self._safe_float(
            metadata.get("strategy_winrate"),
            default=100.0,
        )

        if strategy_winrate < 35:
            return ArbitrationDecision(
                action=ArbitrationAction.REJECT,
                reason="weak historical strategy performance",
                details={"strategy_winrate": strategy_winrate},
            )

        final_grade = self._regrade(
            adjusted_score=adjusted_score,
            confidence=assessment.confidence,
            rr=assessment.risk_reward,
        )

        details = {
            "grade": final_grade.value,
            "effective_score": round(adjusted_score, 2),
            "market_regime": regime,
            "confidence": assessment.confidence,
            "risk_reward": assessment.risk_reward,
        }

        if final_grade in {
            OpportunityGrade.A_PLUS,
            OpportunityGrade.A,
        }:
            return ArbitrationDecision(
                action=ArbitrationAction.TAKE,
                reason="qualified opportunity",
                details=details,
            )

        if final_grade == OpportunityGrade.B:
            return ArbitrationDecision(
                action=ArbitrationAction.WAIT,
                reason="approval candidate",
                details=details,
            )

        return ArbitrationDecision(
            action=ArbitrationAction.REJECT,
            reason="opportunity classified as C-grade",
            details=details,
        )

    def _check_regime_memory_performance(
        self,
        signal: Any,
        context: DecisionContext,
    ) -> Optional[ArbitrationDecision]:
        memory = getattr(context, "regime_memory", None)

        if memory is None:
            return None

        metadata = getattr(signal, "metadata", {}) or {}

        strategy_id = str(
            getattr(signal, "strategy", None)
            or getattr(signal, "strategy_id", None)
            or metadata.get("strategy")
            or metadata.get("strategy_id")
            or "UNKNOWN"
        ).upper()

        regime = str(
            getattr(context, "market_regime", None) or "UNKNOWN"
        ).upper()

        if hasattr(memory, "strategy_metrics"):
            metrics = memory.strategy_metrics(strategy_id, regime)

            trades = int(metrics.get("trades", 0))
            win_rate = float(metrics.get("win_rate", 0.0))
            avg_pnl = float(metrics.get("avg_pnl", 0.0))
            pf = float(metrics.get("pf", 1.0))

            if trades >= 10 and win_rate < 0.30 and avg_pnl < 0:
                return ArbitrationDecision(
                    action=ArbitrationAction.REJECT,
                    reason="weak historical strategy performance",
                    details={
                        "strategy": strategy_id,
                        "regime": regime,
                        "trades": trades,
                        "win_rate": win_rate,
                        "avg_pnl": avg_pnl,
                        "pf": pf,
                    },
                )

        return None

    def _select_best_signal(
        self,
        signals: List[Any],
    ) -> Any:
        def score(signal: Any) -> float:
            confidence = self._safe_float(
                getattr(signal, "confidence", 0.0),
                default=0.0,
            )

            metadata = getattr(signal, "metadata", {}) or {}

            rr = self._safe_float(
                metadata.get("risk_reward", metadata.get("rr", 1.0)),
                default=1.0,
            )

            score_value = self._safe_float(
                metadata.get("score"),
                default=0.0,
            )

            time_bonus = 0.0
            time_of_day = str(
                metadata.get("time_of_day", "")
            ).upper()

            if time_of_day == "AFTERNOON":
                time_bonus = 12.0

            profile_bonus = 0.0
            profile = str(
                getattr(signal, "profile", "")
            ).upper()

            if profile in {
                "SWING",
                "POSITION",
                "MULTIBAGGER",
            }:
                profile_bonus = 8.0

            premium_bonus = 0.0
            if metadata.get("premium"):
                premium_bonus = 10.0

            return (
                score_value
                + confidence * 100.0
                + rr * 10.0
                + time_bonus
                + profile_bonus
                + premium_bonus
            )

        return max(signals, key=score)

    def _check_correlation_guard(
        self,
        signals: List[Any],
        context: DecisionContext,
    ) -> Optional[ArbitrationDecision]:
        guard = getattr(context, "correlation_guard", None)

        if guard is None:
            return None

        for signal in signals:
            metadata = getattr(signal, "metadata", {}) or {}

            thesis = metadata.get("thesis")
            group = metadata.get("correlation_group")
            amount = self._safe_float(
                metadata.get("notional"),
                default=0.0,
            )

            allowed, reason = guard.evaluate(
                thesis=thesis,
                amount=amount,
                group=group,
            )

            if not allowed:
                return ArbitrationDecision(
                    action=ArbitrationAction.REJECT,
                    reason=reason,
                    details={
                        "thesis": thesis,
                        "group": group,
                        "amount": amount,
                    },
                )

        return None

    def _regime_priority_adjustment(
        self,
        signal: Any,
        regime: str,
    ) -> Dict[str, Any]:
        strategy = str(
            getattr(signal, "strategy", "")
        ).upper()

        if strategy in {
            "MEAN_REVERT",
            "MEAN_REVERSION",
            "COUNTER_TREND",
        } and regime in {
            "TRENDING_BULLISH",
            "TRENDING_BEARISH",
            "VOLATILE_BREAKOUT",
        }:
            return {
                "priority": -12.0,
                "reason": "strategy-regime mismatch",
            }

        if strategy in {
            "TREND_FOLLOW",
            "BREAKOUT",
        } and regime == "RANGE_BOUND":
            return {
                "priority": -8.0,
                "reason": "range incompatibility",
            }

        if strategy in {
            "MOMENTUM",
            "MOMENTUM_BREAKOUT",
        } and regime == "RANGE_BOUND":
            return {
                "priority": 4.0,
                "reason": "range breakout bonus",
            }

        return {
            "priority": 0.0,
            "reason": "neutral",
        }

    def _extract_regime_confidence(
        self,
        context: DecisionContext,
    ) -> float:
        value = getattr(context, "regime_confidence", None)

        if value is not None:
            return self._safe_float(value, default=0.60)

        metadata = getattr(context, "metadata", {}) or {}

        return self._safe_float(
            metadata.get("regime_confidence"),
            default=0.60,
        )

    def _high_confidence_signal(
        self,
        signal: Any,
    ) -> bool:
        confidence = self._safe_float(
            getattr(signal, "confidence", 0.0),
            default=0.0,
        )
        return confidence >= 0.88

    def _regrade(
        self,
        adjusted_score: float,
        confidence: float,
        rr: float,
    ) -> OpportunityGrade:
        if adjusted_score >= 85 and confidence >= 0.80 and rr >= 1.40:
            return OpportunityGrade.A_PLUS

        if adjusted_score >= 70 and confidence >= 0.70 and rr >= 1.20:
            return OpportunityGrade.A

        if adjusted_score >= 50 and confidence >= 0.55:
            return OpportunityGrade.B

        return OpportunityGrade.C

    def _safe_float(
        self,
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default