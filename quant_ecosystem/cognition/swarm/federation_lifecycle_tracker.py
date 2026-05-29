from typing import List

from .initiative_lifecycle_record import (
    InitiativeLifecycleRecord,
)
from .initiative_lifecycle_state import (
    InitiativeLifecycleState,
)


class FederationLifecycleTracker:

    def __init__(self):
        self._records: List[
            InitiativeLifecycleRecord
        ] = []

    def register(
        self,
        record: InitiativeLifecycleRecord,
    ) -> None:

        self._records.append(record)

    def count(self) -> int:

        return len(self._records)

    def active_count(self) -> int:

        return sum(
            1
            for record in self._records
            if record.state
            == InitiativeLifecycleState.ACTIVE
        )