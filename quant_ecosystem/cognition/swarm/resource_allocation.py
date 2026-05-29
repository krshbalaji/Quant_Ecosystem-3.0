from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAllocation:
    organism_id: str
    resource_type: str
    approved_amount: float