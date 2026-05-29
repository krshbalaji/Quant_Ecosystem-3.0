from typing import List

from .strategic_vote import StrategicVote


class ConstitutionalCoordinationEngine:

    def evaluate(
        self,
        votes: List[StrategicVote],
        approval_threshold: float = 0.60,
    ):

        if not votes:
            return {
                "outcome": "no_consensus",
                "confidence": 0.0,
            }

        approve = sum(
            vote.weight
            for vote in votes
            if vote.decision == "approve"
        )

        reject = sum(
            vote.weight
            for vote in votes
            if vote.decision == "reject"
        )

        total = approve + reject

        if total == 0:
            return {
                "outcome": "abstained",
                "confidence": 0.0,
            }

        approval_ratio = approve / total

        outcome = (
            "approved"
            if approval_ratio >= approval_threshold
            else "rejected"
        )

        return {
            "outcome": outcome,
            "confidence": approval_ratio,
        }