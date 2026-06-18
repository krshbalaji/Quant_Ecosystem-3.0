from __future__ import annotations

from typing import Any, Protocol


class SupportsSnapshotRepository(Protocol):
    def save_snapshot(
        self,
        name: str,
        snapshot: Any,
    ) -> None:
        ...

    def load_snapshot(
        self,
        name: str,
    ) -> Any:
        ...

    def clear(self) -> None:
        ...