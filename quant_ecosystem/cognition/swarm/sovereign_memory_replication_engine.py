from typing import Optional

from .distributed_memory_mesh import (
    DistributedMemoryMesh,
)
from .federation_memory_contract import (
    FederationMemoryContract,
)
from .federation_memory_snapshot import (
    FederationMemorySnapshot,
)
from .memory_lineage import MemoryLineage


class SovereignMemoryReplicationEngine:

    def __init__(
        self,
        mesh: DistributedMemoryMesh,
        lineage: MemoryLineage,
    ):
        self.mesh = mesh
        self.lineage = lineage

    def replicate(
        self,
        snapshot: FederationMemorySnapshot,
        contract: FederationMemoryContract,
    ) -> bool:

        synchronized = self.mesh.synchronize(
            snapshot,
            contract,
        )

        if not synchronized:
            return False

        self.lineage.append(snapshot)

        return True

    def latest_memory(
        self,
        lineage_id: str,
    ) -> Optional[FederationMemorySnapshot]:

        return self.lineage.latest(lineage_id)