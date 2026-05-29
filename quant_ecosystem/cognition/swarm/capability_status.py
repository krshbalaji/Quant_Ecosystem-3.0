from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityStatus:
    capability_id: str
    active: bool