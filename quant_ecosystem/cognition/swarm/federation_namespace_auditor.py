from .namespace_registry import (
    NamespaceRegistry,
)
from .topology_audit_result import (
    TopologyAuditResult,
)
from quant_ecosystem.core.multimap_store import MultiMapStore


class FederationNamespaceAuditor:

    def __init__(
        self,
    ) -> None:
        self._shadow_store = MultiMapStore()

    def _shadow_key(self) -> str:
        return "audit.topology.namespace_registry"

    def audit(
        self,
        registry: NamespaceRegistry,
    ) -> TopologyAuditResult:

        seen = set()
        duplicates = 0

        for record in registry.records():

            if record.symbol_name in seen:
                duplicates += 1

            seen.add(
                record.symbol_name
            )

        result = TopologyAuditResult(
            total_symbols=registry.count(),
            duplicate_symbols=duplicates,
        )

        try:
            self._shadow_store.put(
                self._shadow_key(),
                result,
            )
        except Exception:
            pass

        return result