from dataclasses import dataclass
from typing import List

from .knowledge_pattern import KnowledgePattern


@dataclass(frozen=True)
class FederationIntelligenceReport:
    pattern_count: int
    patterns: List[KnowledgePattern]