from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDependencyReport:
    dependency_count: int
    isolated_capabilities: int