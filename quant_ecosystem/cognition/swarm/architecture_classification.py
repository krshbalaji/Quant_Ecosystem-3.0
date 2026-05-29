from dataclasses import dataclass

from .architecture_category import (
    ArchitectureCategory,
)


@dataclass(frozen=True)
class ArchitectureClassification:
    component_name: str
    category: ArchitectureCategory