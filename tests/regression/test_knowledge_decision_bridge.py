from quant_ecosystem.cognition.swarm import (
    FederationDecisionRegistry,
    KnowledgeDecisionBridge,
    KnowledgePattern,
)


def test_knowledge_bridge():

    registry = (
        FederationDecisionRegistry()
    )

    result = (
        KnowledgeDecisionBridge()
        .populate(
            [
                KnowledgePattern(
                    category="risk",
                    frequency=3,
                )
            ],
            registry,
        )
    )

    assert result.candidate_count == 1

    assert registry.count() == 1