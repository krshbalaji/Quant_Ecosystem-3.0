from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)

from .execution_lineage import (
    ExecutionLineage,
)


class FederationAuditRegistry(
    KeyedRegistry[
        str,
        ExecutionLineage
    ]
):

    def register(
        self,
        lineage: ExecutionLineage,
    ) -> None:

        super().register(
            lineage.lineage_id,
            lineage,
        )