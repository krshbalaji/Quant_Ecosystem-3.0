from dataclasses import dataclass

from .architecture_trend_direction import (
    ArchitectureTrendDirection,
)


@dataclass(frozen=True)
class ArchitectureTrendReport:
    trend_direction: ArchitectureTrendDirection
    net_change: int