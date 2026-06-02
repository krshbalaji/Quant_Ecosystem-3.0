from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .readiness_status import (
    ReadinessStatus,
)


class FederationReadinessRegistry(
    AppendRegistry[
        ReadinessStatus
    ]
):

    def ready_count(
        self,
    ) -> int:

        return sum(
            1
            for status
            in self.entries()
            if status.ready
        )