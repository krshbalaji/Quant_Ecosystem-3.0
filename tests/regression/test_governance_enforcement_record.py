from quant_ecosystem.cognition.swarm import (
    GovernanceEnforcementRecord,
)


def test_record():

    record = GovernanceEnforcementRecord(
        policy_id="P1",
        outcome="approved",
        compliant=True,
    )

    assert record.compliant