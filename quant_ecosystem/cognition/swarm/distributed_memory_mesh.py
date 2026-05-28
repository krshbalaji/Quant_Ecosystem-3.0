from typing import List

from .federation_memory_snapshot import (
    FederationMemorySnapshot,
)
from .federation_memory_contract import (
    FederationMemoryContract,
)


class DistributedMemoryMesh:

    def __init__(self):
        self.snapshots: List[FederationMemorySnapshot] = []

    def synchronize(
        self,
        snapshot: FederationMemorySnapshot,
        contract: FederationMemoryContract,
    ) -> bool:

        allowed = contract.allows(
            snapshot.memory_type,
            snapshot.constitutional_hash,
        )

        if not allowed:
            return False

        self.snapshots.append(snapshot)

        return True