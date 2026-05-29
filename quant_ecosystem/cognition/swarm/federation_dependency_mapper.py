from .capability_dependency_registry import (
    CapabilityDependencyRegistry,
)
from .capability_dependency_report import (
    CapabilityDependencyReport,
)


class FederationDependencyMapper:

    def analyze(
        self,
        registry: CapabilityDependencyRegistry,
    ) -> CapabilityDependencyReport:

        count = registry.count()

        return CapabilityDependencyReport(
            dependency_count=count,
            isolated_capabilities=0,
        )