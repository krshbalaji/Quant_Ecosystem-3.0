from quant_ecosystem.cognition.swarm import (
    DistributedMemoryMesh,
    FederationMemoryContract,
    FederationMemorySnapshot,
    MemoryLineage,
    SovereignMemoryReplicationEngine,
)


def test_replication_engine_replicates_memory():

    mesh = DistributedMemoryMesh()
    lineage = MemoryLineage()

    engine = SovereignMemoryReplicationEngine(
        mesh,
        lineage,
    )

    contract = FederationMemoryContract(
        contract_id="C-1",
        permitted_memory_types=["temporal"],
        authorized_constitutions=["CONST-A"],
    )

    snapshot = FederationMemorySnapshot(
        organism_id="alpha",
        memory_type="temporal",
        payload={"epoch": 42},
        lineage_id="LINEAGE-1",
        constitutional_hash="CONST-A",
    )

    replicated = engine.replicate(
        snapshot,
        contract,
    )

    assert replicated

    latest = engine.latest_memory("LINEAGE-1")

    assert latest is not None
    assert latest.payload["epoch"] == 42