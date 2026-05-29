from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureComponent:
    component_name: str
    component_type: str