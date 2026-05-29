from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityInventory:
    total_capabilities: int
    active_capabilities: int