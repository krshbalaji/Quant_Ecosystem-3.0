from quant_ecosystem.cognition.swarm import (
    CouncilMember,
    CouncilVote,
    SovereignCouncil,
)


def test_council_resolution():

    council = SovereignCouncil()

    council.register_member(
        CouncilMember("alpha")
    )

    council.register_member(
        CouncilMember("beta")
    )

    resolution = council.decide(
        "RES-1",
        [
            CouncilVote("alpha", "approve"),
            CouncilVote("beta", "approve"),
        ],
    )

    assert resolution.outcome == "approved"