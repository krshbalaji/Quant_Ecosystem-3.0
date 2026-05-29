from .federation_namespace_auditor import (
    FederationNamespaceAuditor,
)
from .namespace_registry import (
    NamespaceRegistry,
)


class FederationTopologyAuditEngine:

    def evaluate(
        self,
        registry: NamespaceRegistry,
    ):

        return (
            FederationNamespaceAuditor()
            .audit(registry)
        )