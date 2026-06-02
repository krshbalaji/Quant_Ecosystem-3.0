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

    def _shadow_key(self, lineage_id: str) -> str:
        return f"audit.execution.lineage.{lineage_id}"

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
            latest_snapshot = self._shadow_store.latest(self._shadow_key(snapshot.lineage_id))
            if latest_snapshot != snapshot:
                self._shadow_store.put(self._shadow_key(snapshot.lineage_id), snapshot)
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
