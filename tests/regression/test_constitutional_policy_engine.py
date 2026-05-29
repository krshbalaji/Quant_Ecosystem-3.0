from quant_ecosystem.cognition.swarm import (
    ConstitutionalPolicyEngine,
    FederationPolicy,
)


def test_policy_engine_detects_violation():

    engine = ConstitutionalPolicyEngine()

    violation = engine.evaluate(
        FederationPolicy(
            policy_id="P1",
            domain="risk",
            minimum_confidence=0.80,
        ),
        confidence=0.50,
    )

    assert violation is not None