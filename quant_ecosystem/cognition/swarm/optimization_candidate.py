from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationCandidate:
    category_name: str
    component_count: int