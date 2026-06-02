from typing import Dict, List

from .federation_memory_snapshot import (
    FederationMemorySnapshot,
)
from quant_ecosystem.core.multimap_store import MultiMapStore


class MemoryLineage:

    def __init__(self):
        # legacy in-memory storage (reads must continue to use this)
        self._lineages: Dict[str, List[FederationMemorySnapshot]] = {}
        # shadow multimap store for parity writes (non-primary)
        self._shadow_store = MultiMapStore()

    def append(
        self,
        snapshot: FederationMemorySnapshot,
    ) -> None:

        # legacy write (primary)
        self._lineages.setdefault(
            snapshot.lineage_id,
            [],
        )

        self._lineages[snapshot.lineage_id].append(snapshot)

        # shadow write to MultiMapStore for migration parity
        try:
            self._shadow_store.put(snapshot.lineage_id, snapshot)
        except Exception:
            # silently ignore shadow store errors to avoid changing behavior
            pass

    def get_lineage(
        self,
        lineage_id: str,
    ) -> List[FederationMemorySnapshot]:

        return self._lineages.get(lineage_id, [])

    def latest(
        self,
        lineage_id: str,
    ):

        lineage = self.get_lineage(lineage_id)

        if not lineage:
            return None

        return lineage[-1]
