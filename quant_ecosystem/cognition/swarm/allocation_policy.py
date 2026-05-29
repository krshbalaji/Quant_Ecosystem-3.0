from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationPolicy:
    resource_type: str
    maximum_allocation: float