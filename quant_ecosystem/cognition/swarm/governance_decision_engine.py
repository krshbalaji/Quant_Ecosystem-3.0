from typing import Dict, List

from .council_member import CouncilMember
from .council_vote import CouncilVote


class GovernanceDecisionEngine:

    def evaluate(
        self,
        members: List[CouncilMember],
        votes: List[CouncilVote],
        approval_threshold: float = 0.60,
    ) -> Dict:

        weights = {
            member.organism_id: member.voting_weight
            for member in members
        }

        approve_weight = 0.0
        reject_weight = 0.0

        for vote in votes:

            weight = weights.get(
                vote.organism_id,
                0.0,
            )

            if vote.decision == "approve":
                approve_weight += weight

            elif vote.decision == "reject":
                reject_weight += weight

        total = approve_weight + reject_weight

        if total == 0:
            return {
                "outcome": "abstained",
                "confidence": 0.0,
            }

        confidence = approve_weight / total

        outcome = (
            "approved"
            if confidence >= approval_threshold
            else "rejected"
        )

        return {
            "outcome": outcome,
            "confidence": confidence,
        }