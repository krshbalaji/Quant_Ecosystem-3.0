from typing import List

from .readiness_status import (
    ReadinessStatus,
)


class FederationReadinessRegistry:

    def __init__(self):
        self._statuses: List[
            ReadinessStatus
        ] = []

    def register(
        self,
        status: ReadinessStatus,
    ) -> None:

        self._statuses.append(
            status
        )

    def count(self) -> int:

        return len(
            self._statuses
        )

    def ready_count(self) -> int:

        return sum(
            1
            for status
            in self._statuses
            if status.ready
        )