from quant_ecosystem.consensus.consensus_vote import (
    ConsensusVote,
)

from quant_ecosystem.consensus.consensus_registry import (
    consensus_registry,
)


class ConsensusEngine:

    def vote(
        self,
        *,
        source,
        approved,
        confidence,
    ):

        consensus_registry.register(
            ConsensusVote(
                source=source,
                approved=approved,
                confidence=confidence,
            )
        )

    def approved(self):

        votes = (
            consensus_registry.votes()
        )

        if not votes:
            return True

        approvals = sum(
            1
            for v in votes
            if v.approved
        )

        avg_confidence = (
            sum(
                v.confidence
                for v in votes
            )
            / len(votes)
        )

        consensus_registry.clear()

        return (
            approvals
            >= max(
                1,
                len(votes) // 2,
            )
            and avg_confidence >= 0.5
        )


consensus_engine = (
    ConsensusEngine()
)