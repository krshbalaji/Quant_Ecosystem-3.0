from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityMetric:
    category_name: str
    total_capacity: float
    utilized_capacity: float