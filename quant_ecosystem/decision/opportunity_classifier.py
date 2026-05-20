from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class OpportunityGrade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"


@dataclass
class OpportunityAssessment:
    grade: OpportunityGrade
    effective_score: float
    confidence: float
    risk_reward: float
    regime_bonus: float
    reasons: list[str]


class OpportunityClassifier:
    """
    QE3 opportunity classifier

    Compatible with:
    - lightweight TradingView payloads
    - QE3 organism scoring
    - legacy arbitration engine expectations
    """

    def classify(
        self,
        signal_intent: Any,
        market_regime: str,
        profile: Optional[Any] = None,
    ) -> OpportunityAssessment:
        metadata = getattr(signal_intent, "metadata", {}) or {}

        confidence = self._safe_float(
            getattr(signal_intent, "confidence", None),
            default=0.50,
        )

        score = self._safe_float(
            metadata.get("score"),
            default=0.0,
        )

        risk_reward = self._extract_risk_reward(metadata)

        premium = bool(metadata.get("premium", False))

        threshold = 50.0

        if profile is not None:
            threshold = self._safe_float(
                getattr(profile, "min_score_threshold", 50.0),
                default=50.0,
            )

        regime_bonus, regime_reason = self._compute_regime_bonus(
            signal_intent=signal_intent,
            market_regime=market_regime,
        )

        # TradingView compatibility:
        # no score? derive from confidence
        if score > 0:
            base_score = score
            score_reason = f"explicit score={score:.2f}"
        else:
            base_score = confidence * 70.0
            score_reason = f"inferred score={base_score:.2f}"

        effective_score = (
            base_score
            + min(risk_reward, 3.0) * 12.0
            + regime_bonus * 8.0
        )

        reasons = [
            score_reason,
            f"rr={risk_reward:.2f}",
            f"regime={market_regime}",
        ]

        if regime_reason:
            reasons.append(regime_reason)

        # Premium fast lane
        if (
            premium
            and effective_score >= threshold + 20
            and confidence >= 0.80
            and risk_reward >= 1.50
        ):
            reasons.append("premium qualified")
            return OpportunityAssessment(
                grade=OpportunityGrade.A_PLUS,
                effective_score=effective_score,
                confidence=confidence,
                risk_reward=risk_reward,
                regime_bonus=regime_bonus,
                reasons=reasons,
            )

        # A+
        if (
            effective_score >= threshold + 20
            and confidence >= 0.85
            and risk_reward >= 1.50
        ):
            reasons.append("elite opportunity")
            return OpportunityAssessment(
                grade=OpportunityGrade.A_PLUS,
                effective_score=effective_score,
                confidence=confidence,
                risk_reward=risk_reward,
                regime_bonus=regime_bonus,
                reasons=reasons,
            )

        # A
        if (
            effective_score >= threshold + 10
            and confidence >= 0.72
            and risk_reward >= 1.20
        ):
            reasons.append("qualified opportunity")
            return OpportunityAssessment(
                grade=OpportunityGrade.A,
                effective_score=effective_score,
                confidence=confidence,
                risk_reward=risk_reward,
                regime_bonus=regime_bonus,
                reasons=reasons,
            )

        # B
        if (
            effective_score >= threshold - 5
            and confidence >= 0.55
        ):
            reasons.append("watch candidate")
            return OpportunityAssessment(
                grade=OpportunityGrade.B,
                effective_score=effective_score,
                confidence=confidence,
                risk_reward=risk_reward,
                regime_bonus=regime_bonus,
                reasons=reasons,
            )

        reasons.append("weak edge")

        return OpportunityAssessment(
            grade=OpportunityGrade.C,
            effective_score=effective_score,
            confidence=confidence,
            risk_reward=risk_reward,
            regime_bonus=regime_bonus,
            reasons=reasons,
        )

    def _compute_regime_bonus(
        self,
        signal_intent: Any,
        market_regime: str,
    ) -> tuple[float, str]:
        regime = str(market_regime or "").upper()
        side = str(getattr(signal_intent, "side", "")).upper()
        strategy = str(getattr(signal_intent, "strategy", "")).upper()

        bonus = 0.0
        reason = ""

        if regime in {"TRENDING_BULLISH", "BULL"} and side == "BUY":
            bonus += 1.0
            reason = "bull alignment"

        elif regime in {"TRENDING_BEARISH", "BEAR"} and side == "SELL":
            bonus += 1.0
            reason = "bear alignment"

        elif regime == "VOLATILE_BREAKOUT":
            bonus += 1.0
            reason = "breakout regime"

        elif regime == "TRANSITION":
            bonus += 0.5
            reason = "transition regime"

        elif regime == "RANGE_BOUND":
            if strategy in {
                "BREAKOUT",
                "MOMENTUM",
                "MOMENTUM_BREAKOUT",
            }:
                bonus += 0.25
                reason = "range compression breakout"

        return bonus, reason

    def _extract_risk_reward(
        self,
        metadata: Dict[str, Any],
    ) -> float:
        for key in (
            "risk_reward",
            "rr",
            "reward_risk",
        ):
            value = self._safe_float(
                metadata.get(key),
                default=0.0,
            )
            if value > 0:
                return value

        return 1.0

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