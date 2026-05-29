from quant_ecosystem.cognition.swarm import (
    CivilizationKnowledgeBase,
    FederationObservation,
)


def test_knowledge_storage():

    kb = CivilizationKnowledgeBase()

    kb.add(
        FederationObservation(
            "alpha",
            "risk",
            "OBS1",
            {},
        )
    )

    assert kb.count() == 1