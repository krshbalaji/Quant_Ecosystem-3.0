from datetime import datetime

from quant_ecosystem.cognition.swarm.memory_lineage import MemoryLineage
from quant_ecosystem.cognition.swarm.federation_memory_snapshot import (
    FederationMemorySnapshot,
)


def make_snapshot(lineage_id: str, idx: int):
    return FederationMemorySnapshot(
        organism_id="org1",
        memory_type="typeA",
        payload={"v": idx},
        lineage_id=lineage_id,
        constitutional_hash=f"h{idx}",
        created_at=datetime.utcnow(),
    )


def test_memory_lineage_shadow_parity_append_get_latest():
    ml = MemoryLineage()

    s1 = make_snapshot("L1", 1)
    s2 = make_snapshot("L1", 2)

    ml.append(s1)
    ml.append(s2)

    # Legacy reads unchanged
    legacy = ml.get_lineage("L1")
    assert legacy == [s1, s2]
    assert ml.latest("L1") == s2

    # Shadow store has same sequence
    shadow_key = "audit.execution.lineage.L1"
    shadow_get = ml._shadow_store.get(shadow_key)
    assert shadow_get == [s1, s2]
    assert ml._shadow_store.latest(shadow_key) == s2
