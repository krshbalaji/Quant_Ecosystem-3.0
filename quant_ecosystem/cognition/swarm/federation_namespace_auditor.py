from .namespace_registry import (
    NamespaceRegistry,
)
from .topology_audit_result import (
    TopologyAuditResult,
)


class FederationNamespaceAuditor:

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

        return TopologyAuditResult(
            total_symbols=registry.count(),
            duplicate_symbols=duplicates,
        )