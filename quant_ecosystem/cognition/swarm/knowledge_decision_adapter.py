from .decision_candidate import (
    DecisionCandidate,
)
from .knowledge_pattern import (
    KnowledgePattern,
)


class KnowledgeDecisionAdapter:

    def adapt(
        self,
        pattern: KnowledgePattern,
    ) -> DecisionCandidate:

        return DecisionCandidate(
            category_name=(
                pattern.category
            ),
            priority_score=float(
                pattern.frequency
            ),
        )