from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyEdge:
    source_component: str
    target_component: str