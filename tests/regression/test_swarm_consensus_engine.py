from quant_ecosystem.cognition.swarm import (
    SwarmConsensusEngine,
)


def test_swarm_consensus_computation():

    engine = SwarmConsensusEngine()

    result = engine.compute_consensus([
        {
            "decision": "approve",
            "weight": 2.0,
        },
        {
            "decision": "approve",
            "weight": 1.0,
        },
        {
            "decision": "reject",
            "weight": 1.0,
        },
    ])

    assert result["consensus"] == "approve"
    assert result["participants"] == 3
    assert result["confidence"] > 0.5