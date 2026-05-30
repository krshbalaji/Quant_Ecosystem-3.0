from quant_ecosystem.cognition.swarm import (
    KnowledgeDecisionAdapter,
    KnowledgePattern,
)


def test_knowledge_adapter():

    candidate = (
        KnowledgeDecisionAdapter()
        .adapt(
            KnowledgePattern(
                category="risk",
                frequency=5,
            )
        )
    )

    assert candidate.priority_score == 5.0