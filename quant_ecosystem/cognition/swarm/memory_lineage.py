from typing import Dict, List

from .federation_memory_snapshot import (
    FederationMemorySnapshot,
)


class MemoryLineage:

    def __init__(self):
        self._lineages: Dict[str, List[FederationMemorySnapshot]] = {}

    def append(
        self,
        snapshot: FederationMemorySnapshot,
    ) -> None:

        self._lineages.setdefault(
            snapshot.lineage_id,
            [],
        )

        self._lineages[snapshot.lineage_id].append(snapshot)

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