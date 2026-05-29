from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureTrendPoint:
    sequence: int
    component_count: int