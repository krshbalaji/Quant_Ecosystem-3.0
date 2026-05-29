from quant_ecosystem.cognition.swarm import (
    StrategicProposal,
    StrategicVote,
    SwarmStrategyCoordinator,
)


def test_strategy_coordination():

    coordinator = SwarmStrategyCoordinator()

    proposal = StrategicProposal(
        proposal_id="P1",
        domain="capital",
        title="Capital Allocation",
        payload={},
    )

    record = coordinator.coordinate(
        proposal,
        [
            StrategicVote("a", "approve"),
            StrategicVote("b", "approve"),
            StrategicVote("c", "reject"),
        ],
    )

    assert record.outcome == "approved"