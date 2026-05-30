from typing import List

from .performance_snapshot import (
    PerformanceSnapshot,
)


class FederationPerformanceRegistry:

    def __init__(self):
        self._snapshots: List[
            PerformanceSnapshot
        ] = []

    def register(
        self,
        snapshot: PerformanceSnapshot,
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