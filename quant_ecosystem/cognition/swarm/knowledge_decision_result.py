from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeDecisionResult:
    candidate_count: int