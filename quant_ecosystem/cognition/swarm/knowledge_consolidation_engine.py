from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from quant_ecosystem.core.multimap_store import MultiMapStore

from .knowledge_pattern import KnowledgePattern
from .learning_pattern import LearningPattern


class KnowledgeConsolidationEngine:

    def consolidate(
        self,
        patterns: Sequence[LearningPattern],
        group_by: str = "classification_key",
    ) -> List[KnowledgePattern]:

        grouped = self._group_patterns(patterns, group_by)

        return [
            self._build_knowledge_pattern(group_key, group_patterns)
            for group_key, group_patterns in grouped.items()
        ]

    def persist(
        self,
        store: MultiMapStore,
        knowledge_patterns: Sequence[KnowledgePattern],
    ) -> None:

        for pattern in knowledge_patterns:
            store.put(
                f"audit.learning.pattern.{pattern.pattern_id or pattern.category}",
                pattern,
            )

    def group_by_type(
        self,
        patterns: Sequence[LearningPattern],
    ) -> Dict[str, List[LearningPattern]]:

        return self._group_patterns(patterns, "pattern_type")

    def group_by_category(
        self,
        patterns: Sequence[LearningPattern],
    ) -> Dict[str, List[LearningPattern]]:

        return self._group_patterns(patterns, "classification_key")

    def _group_patterns(
        self,
        patterns: Iterable[LearningPattern],
        group_by: str,
    ) -> Dict[str, List[LearningPattern]]:

        grouped: Dict[str, List[LearningPattern]] = defaultdict(list)

        for pattern in patterns:
            bucket = getattr(pattern, group_by, None)
            if bucket is None:
                bucket = pattern.classification_key or pattern.pattern_id or "unknown"
            grouped[bucket].append(pattern)

        return grouped

    def _build_knowledge_pattern(
        self,
        group_key: str,
        patterns: Sequence[LearningPattern],
    ) -> KnowledgePattern:

        source_keys = tuple(
            sorted(
                {
                    pattern.source_key
                    for pattern in patterns
                    if pattern.source_key is not None
                }
            )
        )

        provenance = tuple(
            sorted(
                {
                    pattern.pattern_id
                    for pattern in patterns
                    if pattern.pattern_id is not None
                }
            )
        )

        schema_versions = tuple(
            sorted(
                {
                    version
                    for pattern in patterns
                    for version in pattern.schema_versions
                }
            )
        )

        first_seen = min(
            (
                pattern.first_seen
                for pattern in patterns
                if pattern.first_seen is not None
            ),
            default=None,
        )

        last_seen = max(
            (
                pattern.last_seen
                for pattern in patterns
                if pattern.last_seen is not None
            ),
            default=None,
        )

        return KnowledgePattern(
            category=group_key,
            frequency=sum(pattern.frequency for pattern in patterns),
            pattern_id=f"knowledge.{group_key}",
            pattern_type=patterns[0].pattern_type or "consolidated",
            source_keys=source_keys,
            aggregated_count=len(patterns),
            first_seen=first_seen,
            last_seen=last_seen,
            schema_versions=schema_versions,
            provenance=provenance,
            metadata={
                "input_pattern_count": len(patterns),
                "anomaly_count": sum(pattern.anomaly_count for pattern in patterns),
                "repeated_event_count": sum(pattern.repeated_event_count for pattern in patterns),
            },
        )
