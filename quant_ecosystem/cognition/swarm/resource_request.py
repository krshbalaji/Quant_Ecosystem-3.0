from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceRequest:
    organism_id: str
    resource_type: str
    requested_amount: float