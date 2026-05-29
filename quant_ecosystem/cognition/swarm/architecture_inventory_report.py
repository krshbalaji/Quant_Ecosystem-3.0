from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureInventoryReport:
    total_components: int
    unique_types: int