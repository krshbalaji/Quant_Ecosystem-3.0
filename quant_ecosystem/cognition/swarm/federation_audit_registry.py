from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)
from quant_ecosystem.core.multimap_store import MultiMapStore

from .execution_lineage import (
    ExecutionLineage,
)


class FederationAuditRegistry(
    KeyedRegistry[
        str,
        ExecutionLineage
    ]
):

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self._shadow_store = MultiMapStore()

    def _shadow_key(self) -> str:
        return "audit.execution.lineage_registry"

    def register(
        self,
        lineage: ExecutionLineage,
    ) -> None:

        super().register(
            lineage.lineage_id,
            lineage,
        )

        try:
            self._shadow_store.put(
                self._shadow_key(),
                lineage.lineage_id,
            )
        except Exception:
            pass