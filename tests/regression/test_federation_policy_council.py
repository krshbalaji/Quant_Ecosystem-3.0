from quant_ecosystem.cognition.swarm import (
    FederationPolicy,
    FederationPolicyCouncil,
)


def test_policy_council_approves():

    council = FederationPolicyCouncil()

    result = council.enforce(
        FederationPolicy(
            policy_id="P1",
            domain="risk",
            minimum_confidence=0.60,
        ),
        confidence=0.90,
    )

    assert result.compliant