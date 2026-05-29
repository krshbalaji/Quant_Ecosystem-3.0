from typing import List

from .namespace_record import (
    NamespaceRecord,
)


class NamespaceRegistry:

    def __init__(self):
        self._records: List[
            NamespaceRecord
        ] = []

    def register(
        self,
        record: NamespaceRecord,
    ) -> None:

        self._records.append(record)

    def count(self) -> int:

        return len(
            self._records
        )

    def records(self):

        return list(
            self._records
        )