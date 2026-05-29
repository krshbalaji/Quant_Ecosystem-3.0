from .capability_dependency_registry import (
    CapabilityDependencyRegistry,
)


class CapabilityReadinessEngine:

    def ready(
        self,
        registry: CapabilityDependencyRegistry,
    ) -> bool:

        return registry.count() >= 0