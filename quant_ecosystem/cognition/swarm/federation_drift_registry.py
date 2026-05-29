from typing import List

from .architecture_snapshot import (
    ArchitectureSnapshot,
)


class FederationDriftRegistry:

    def __init__(self):
        self._snapshots: List[
            ArchitectureSnapshot
        ] = []

    def register(
        self,
        snapshot: ArchitectureSnapshot,
    ) -> None:

        self._snapshots.append(
            snapshot
        )

    def snapshots(self):

        return list(
            self._snapshots
        )

    def count(self) -> int:

        return len(
            self._snapshots
        )