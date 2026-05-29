from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureInventory:
    total_components: int
    total_component_types: int