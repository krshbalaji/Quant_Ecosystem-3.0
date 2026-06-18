from __future__ import annotations

from typing import Any, Protocol


class SupportsStrategyEngine(Protocol):
    def evaluate(
        self,
        snapshots: list[Any],
        market_bias: str,
        regime: str,
    ) -> list[Any]:
        ...