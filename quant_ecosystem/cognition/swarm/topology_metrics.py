from dataclasses import dataclass


@dataclass(frozen=True)
class TopologyMetrics:
    component_count: int
    dependency_count: int