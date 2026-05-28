from quant_ecosystem.cognition.swarm import (
    DistributedMemoryMesh,
    FederationMemoryContract,
    FederationMemorySnapshot,
)


def test_distributed_memory_mesh_accepts_valid_contract():

    mesh = DistributedMemoryMesh()

    contract = FederationMemoryContract(
        contract_id="C-1",
        permitted_memory_types=["strategic"],
        authorized_constitutions=["CONST-A"],
    )

    snapshot = FederationMemorySnapshot(
        organism_id="alpha",
        memory_type="strategic",
        payload={"signal": "approved"},
        lineage_id="L-1",
        constitutional_hash="CONST-A",
    )

    accepted = mesh.synchronize(
        snapshot,
        contract,
    )

    assert accepted
    assert len(mesh.snapshots) == 1


def test_distributed_memory_mesh_rejects_invalid_contract():

    mesh = DistributedMemoryMesh()

    contract = FederationMemoryContract(
        contract_id="C-1",
        permitted_memory_types=["risk"],
        authorized_constitutions=["CONST-X"],
    )

    snapshot = FederationMemorySnapshot(
        organism_id="alpha",
        memory_type="strategic",
        payload={},
        lineage_id="L-2",
        constitutional_hash="CONST-A",
    )

    accepted = mesh.synchronize(
        snapshot,
        contract,
    )

    assert not accepted
    assert len(mesh.snapshots) == 0