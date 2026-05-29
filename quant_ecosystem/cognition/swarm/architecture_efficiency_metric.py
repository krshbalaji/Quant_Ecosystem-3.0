from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureEfficiencyMetric:
    category_name: str
    utilized_components: int
    total_components: int