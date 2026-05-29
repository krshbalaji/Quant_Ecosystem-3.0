from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureOptimizationReport:
    target_category: str
    component_count: int