from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDensitySnapshot:
    total_components: int
    total_categories: int