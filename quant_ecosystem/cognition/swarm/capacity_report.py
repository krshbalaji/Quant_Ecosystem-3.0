from dataclasses import dataclass


@dataclass(frozen=True)
class CapacityReport:
    highest_utilization_category: str
    utilization_ratio: float