from quant_ecosystem.cognition.swarm import (
    DiplomaticPosition,
    DiplomaticTreaty,
    SovereignDiplomaticCouncil,
)


def test_diplomatic_council_uses_treaty_support():

    council = SovereignDiplomaticCouncil()

    treaty = DiplomaticTreaty(
        treaty_id="T-1",
        participating_organisms=[
            "alpha",
            "beta",
        ],
        permitted_domains=[
            "liquidity",
        ],
    )

    council.register_treaty(treaty)

    left = DiplomaticPosition(
        organism_id="alpha",
        objectives={
            "liquidity": 0.9,
        },
    )

    right = DiplomaticPosition(
        organism_id="beta",
        objectives={
            "liquidity": 0.88,
        },
    )

    result = council.evaluate_interaction(
        left,
        right,
        "liquidity",
    )

    assert result["treaty_supported"]
    assert result["resolution"] == "cooperate"