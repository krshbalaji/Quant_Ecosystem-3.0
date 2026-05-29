from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDensityReport:
    densest_category: str
    component_count: int