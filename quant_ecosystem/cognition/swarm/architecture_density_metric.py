from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDensityMetric:
    category_name: str
    component_count: int