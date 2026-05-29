from typing import List

from .council_member import CouncilMember
from .council_vote import CouncilVote
from .governance_resolution import (
    GovernanceResolution,
)
from .governance_decision_engine import (
    GovernanceDecisionEngine,
)


class SovereignCouncil:

    def __init__(self):
        self.members: List[CouncilMember] = []
        self.engine = GovernanceDecisionEngine()

    def register_member(
        self,
        member: CouncilMember,
    ) -> None:

        self.members.append(member)

    def decide(
        self,
        resolution_id: str,
        votes: List[CouncilVote],
    ) -> GovernanceResolution:

        result = self.engine.evaluate(
            self.members,
            votes,
        )

        return GovernanceResolution(
            resolution_id=resolution_id,
            outcome=result["outcome"],
            confidence=result["confidence"],
            participant_count=len(votes),
        )