from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyAnalysisResult:
    dependency_density: float
    isolated_components: int