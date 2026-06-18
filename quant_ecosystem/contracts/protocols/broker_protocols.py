from __future__ import annotations

from typing import Any, Protocol


class SupportsBroker(Protocol):
    def place_order(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def cancel_order(self, *args: Any, **kwargs: Any) -> Any:
        ...