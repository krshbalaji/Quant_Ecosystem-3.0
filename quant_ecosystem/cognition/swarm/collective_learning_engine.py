from collections import Counter
from typing import List

from .federation_observation import FederationObservation
from .knowledge_pattern import KnowledgePattern


class CollectiveLearningEngine:

    def discover_patterns(
        self,
        observations: List[FederationObservation],
    ) -> List[KnowledgePattern]:

        counter = Counter(
            obs.category
            for obs in observations
        )

        return [
            KnowledgePattern(
                category=category,
                frequency=count,
            )
            for category, count
            in counter.items()
        ]