from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityHealth:
    capability_id: str
    healthy: bool