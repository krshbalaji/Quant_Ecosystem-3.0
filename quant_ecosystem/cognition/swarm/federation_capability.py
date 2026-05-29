from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCapability:
    capability_id: str
    capability_type: str
    active: bool = True