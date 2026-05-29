from quant_ecosystem.cognition.swarm import (
    DecisionCandidate,
    FederationDecisionRegistry,
)


def test_decision_registry():

    registry = (
        FederationDecisionRegistry()
    )

    registry.register(
        DecisionCandidate(
            category_name="governance",
            priority_score=9.0,
        )
    )

    assert registry.count() == 1