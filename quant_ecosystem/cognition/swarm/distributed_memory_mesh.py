from typing import List

from .federation_memory_snapshot import (
    FederationMemorySnapshot,
)
from .federation_memory_contract import (
    FederationMemoryContract,
)
from quant_ecosystem.core.multimap_store import MultiMapStore


class DistributedMemoryMesh:

    def __init__(self):
        self.snapshots: List[FederationMemorySnapshot] = []
        self._shadow_store = MultiMapStore()

    def _shadow_key(self, snapshot: FederationMemorySnapshot) -> str:
        return f"audit.execution.lineage.{snapshot.lineage_id}"

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

        try:
            self._shadow_store.put(
                self._shadow_key(snapshot),
                snapshot,
            )
        except Exception:
            pass

        return True