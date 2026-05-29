from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyHealthReport:
    healthy: bool
    dependency_density: float