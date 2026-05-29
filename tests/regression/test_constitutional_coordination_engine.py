from quant_ecosystem.cognition.swarm import (
    ConstitutionalCoordinationEngine,
    StrategicVote,
)


def test_approval_threshold():

    engine = ConstitutionalCoordinationEngine()

    result = engine.evaluate(
        [
            StrategicVote("a", "approve"),
            StrategicVote("b", "approve"),
            StrategicVote("c", "reject"),
        ]
    )

    assert result["outcome"] == "approved"