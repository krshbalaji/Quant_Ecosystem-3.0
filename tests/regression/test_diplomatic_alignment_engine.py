from quant_ecosystem.cognition.swarm import (
    DiplomaticAlignmentEngine,
    DiplomaticPosition,
)


def test_alignment_engine_scores_alignment():

    engine = DiplomaticAlignmentEngine()

    left = DiplomaticPosition(
        organism_id="alpha",
        objectives={
            "capital": 0.9,
        },
    )

    right = DiplomaticPosition(
        organism_id="beta",
        objectives={
            "capital": 0.8,
        },
    )

    alignment = engine.evaluate_alignment(
        left,
        right,
        "capital",
    )

    assert alignment > 0.8