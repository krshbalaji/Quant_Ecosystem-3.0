from typing import Dict

from .execution_lineage import ExecutionLineage


class FederationAuditRegistry:

    def __init__(self):
        self._registry: Dict[str, ExecutionLineage] = {}

    def register(
        self,
        lineage: ExecutionLineage,
    ) -> None:

        self._registry[
            lineage.lineage_id
        ] = lineage

    def get(
        self,
        lineage_id: str,
    ):

        return self._registry.get(lineage_id)

    def exists(
        self,
        lineage_id: str,
    ) -> bool:

        return lineage_id in self._registry