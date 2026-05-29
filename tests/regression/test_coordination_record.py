from quant_ecosystem.cognition.swarm import (
    CoordinationRecord,
)


def test_record_creation():

    record = CoordinationRecord(
        proposal_id="P1",
        outcome="approved",
        confidence=0.8,
        participant_count=3,
    )

    assert record.proposal_id == "P1"