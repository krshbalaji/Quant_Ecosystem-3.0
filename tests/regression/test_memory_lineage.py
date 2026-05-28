from quant_ecosystem.cognition.swarm import (
    FederationMemorySnapshot,
    MemoryLineage,
)


def test_memory_lineage_tracks_snapshots():

    lineage = MemoryLineage()

    snapshot = FederationMemorySnapshot(
        organism_id="alpha",
        memory_type="strategic",
        payload={"state": "stable"},
        lineage_id="L-1",
        constitutional_hash="CONST-A",
    )

    lineage.append(snapshot)

    latest = lineage.latest("L-1")

    assert latest is not None
    assert latest.payload["state"] == "stable"