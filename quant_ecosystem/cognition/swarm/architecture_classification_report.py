from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureClassificationReport:
    total_components: int
    total_categories: int