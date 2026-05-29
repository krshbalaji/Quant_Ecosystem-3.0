from dataclasses import dataclass


@dataclass(frozen=True)
class ResolutionReport:
    collision_count: int
    resolution_count: int