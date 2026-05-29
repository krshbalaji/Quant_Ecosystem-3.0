from quant_ecosystem.cognition.swarm import (
    DecisionCandidate,
    FederationDecisionEngine,
    FederationDecisionRegistry,
)


def test_decision_engine():

    registry = (
        FederationDecisionRegistry()
    )

    registry.register(
        DecisionCandidate(
            category_name="governance",
            priority_score=9.0,
        )
    )

    registry.register(
        DecisionCandidate(
            category_name="topology",
            priority_score=4.0,
        )
    )

    report = (
        FederationDecisionEngine()
        .evaluate(
            registry
        )
    )

    assert (
        report.recommended_category
        == "governance"
    )