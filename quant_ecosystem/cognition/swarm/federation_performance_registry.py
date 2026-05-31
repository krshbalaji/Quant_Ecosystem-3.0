from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .performance_snapshot import (
    PerformanceSnapshot,
)


class FederationPerformanceRegistry(
    AppendRegistry[
        PerformanceSnapshot
    ]
):

    def snapshots(
        self,
    ) -> list[PerformanceSnapshot]:

        return self.entries()