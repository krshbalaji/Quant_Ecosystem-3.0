from typing import List

from .coordination_record import CoordinationRecord
from .constitutional_coordination_engine import (
    ConstitutionalCoordinationEngine,
)
from .strategic_proposal import StrategicProposal
from .strategic_vote import StrategicVote


class SwarmStrategyCoordinator:

    def __init__(self):
        self.engine = ConstitutionalCoordinationEngine()

    def coordinate(
        self,
        proposal: StrategicProposal,
        votes: List[StrategicVote],
    ) -> CoordinationRecord:

        result = self.engine.evaluate(votes)

        return CoordinationRecord(
            proposal_id=proposal.proposal_id,
            outcome=result["outcome"],
            confidence=result["confidence"],
            participant_count=len(votes),
        )