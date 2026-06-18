from __future__ import annotations

from typing import Protocol

from .strategy_protocols import SupportsStrategyEngine


class SupportsRouter(Protocol):
    strategy_engine: SupportsStrategyEngine