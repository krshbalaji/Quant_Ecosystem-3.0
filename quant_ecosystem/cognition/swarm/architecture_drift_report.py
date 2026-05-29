from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDriftReport:
    component_growth: int
    growth_detected: bool