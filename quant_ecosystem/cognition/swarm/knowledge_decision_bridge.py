from .federation_decision_registry import (
    FederationDecisionRegistry,
)
from .knowledge_decision_adapter import (
    KnowledgeDecisionAdapter,
)
from .knowledge_decision_result import (
    KnowledgeDecisionResult,
)


class KnowledgeDecisionBridge:

    def populate(
        self,
        patterns,
        registry: (
            FederationDecisionRegistry
        ),
    ) -> KnowledgeDecisionResult:

        adapter = (
            KnowledgeDecisionAdapter()
        )

        count = 0

        for pattern in patterns:

            registry.register(
                adapter.adapt(
                    pattern
                )
            )

            count += 1

        return KnowledgeDecisionResult(
            candidate_count=count
        )