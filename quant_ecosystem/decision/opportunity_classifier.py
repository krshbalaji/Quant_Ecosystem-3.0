from dataclasses import dataclass
from enum import Enum
from typing import Any

from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.discipline import DisciplineAction, DisciplineDecision
from quant_ecosystem.profiles.base_profile import BaseProfile


class OpportunityGrade(str, Enum):
    C = "C"
    B = "B"
    A = "A"
    A_PLUS = "A+"


@dataclass
class OpportunityClassifier:
    def classify(
        self,
        signal_intent: SignalIntent,
        profile: BaseProfile,
        discipline_decision: DisciplineDecision,
        market_regime: str = "NEUTRAL",
    ) -> OpportunityGrade:
        score = float(signal_intent.metadata.get("score", 0.0))
        confidence = float(signal_intent.confidence or 0.0)
        rr = float(signal_intent.metadata.get("risk_reward") or signal_intent.metadata.get("rr") or 1.0)
        regime_bonus = 0

        if discipline_decision.action == DisciplineAction.REJECT:
            return OpportunityGrade.C

        if discipline_decision.action == DisciplineAction.WAIT:
            return OpportunityGrade.B

        if market_regime.upper() == "BULL" and signal_intent.side == "BUY":
            regime_bonus += 1
        elif market_regime.upper() == "BEAR" and signal_intent.side == "SELL":
            regime_bonus += 1

        effective_score = score + confidence * 20 + min(rr, 3.0) * 10 + regime_bonus * 5

        threshold = float(profile.min_score_threshold or 50)
        premium_flag = bool(signal_intent.metadata.get("premium", False))

        if premium_flag and effective_score >= threshold + 35 and confidence >= 0.80 and rr >= 1.7:
            return OpportunityGrade.A_PLUS

        if effective_score >= threshold + 20 and confidence >= 0.75 and rr >= 1.4:
            return OpportunityGrade.A

        if effective_score >= threshold and confidence >= 0.60:
            return OpportunityGrade.B

        return OpportunityGrade.C

    @staticmethod
    def rank_value(grade: OpportunityGrade) -> int:
        return {
            OpportunityGrade.C: 10,
            OpportunityGrade.B: 20,
            OpportunityGrade.A: 30,
            OpportunityGrade.A_PLUS: 40,
        }[grade]

    def compute_priority(
        self,
        signal_intent: SignalIntent,
        profile: BaseProfile,
        grade: OpportunityGrade,
        discipline_decision: DisciplineDecision,
    ) -> float:
        score = float(signal_intent.metadata.get("score", 0.0))
        return (
            self.rank_value(grade)
            + score * 0.1
            + float(signal_intent.confidence or 0.0) * 5.0
            + discipline_decision.confidence * 2.0
        )
