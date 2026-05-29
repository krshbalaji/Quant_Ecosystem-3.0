from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDependency:
    capability_id: str
    depends_on: str