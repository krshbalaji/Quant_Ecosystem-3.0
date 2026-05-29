from quant_ecosystem.cognition.swarm import (
    CouncilMember,
    CouncilVote,
    GovernanceDecisionEngine,
)


def test_governance_approval():

    engine = GovernanceDecisionEngine()

    result = engine.evaluate(
        [
            CouncilMember("a", 1.0),
            CouncilMember("b", 1.0),
            CouncilMember("c", 1.0),
        ],
        [
            CouncilVote("a", "approve"),
            CouncilVote("b", "approve"),
            CouncilVote("c", "reject"),
        ],
    )

    assert result["outcome"] == "approved"