from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureEfficiencyReport:
    average_efficiency: float
    category_count: int