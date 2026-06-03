from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .audit_replay import AuditReplayResult
from .federation_observation import FederationObservation
from .knowledge_pattern import KnowledgePattern
from .learning_pattern import LearningPattern
from .learning_pattern_registry import LearningPatternRegistry


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

    def extract_patterns(
        self,
        replay_result: AuditReplayResult,
    ) -> List[LearningPattern]:

        records = list(replay_result.records)
        grouped = self._group_records_by_event_type(records)

        return [
            self._build_pattern(
                classification_key=key,
                records=group,
                source_key=replay_result.source_key,
            )
            for key, group in grouped.items()
        ]

    def register_patterns(
        self,
        registry: LearningPatternRegistry,
        patterns: Sequence[LearningPattern],
    ) -> None:

        for pattern in patterns:
            registry.register(pattern)

    def _group_records_by_event_type(
        self,
        records: Iterable[Any],
    ) -> Dict[str, List[Any]]:

        grouped: Dict[str, List[Any]] = {}

        for record in records:
            key = self._record_event_type(record) or self._record_class_name(record)
            grouped.setdefault(key, []).append(record)

        return grouped

    def _record_event_type(
        self,
        record: Any,
    ) -> Optional[str]:

        if hasattr(record, "event_type"):
            return getattr(record, "event_type")

        if isinstance(record, dict):
            return record.get("event_type")

        return None

    def _record_class_name(
        self,
        record: Any,
    ) -> str:

        return type(record).__name__

    def _build_pattern(
        self,
        classification_key: str,
        records: Sequence[Any],
        source_key: Optional[str],
    ) -> LearningPattern:

        timestamps = [
            self._record_timestamp(record)
            for record in records
            if self._record_timestamp(record) is not None
        ]
        first_seen = min(timestamps) if timestamps else None
        last_seen = max(timestamps) if timestamps else None

        schema_versions = tuple(
            sorted(
                {
                    version
                    for record in records
                    for version in [self._record_schema_version(record)]
                    if version is not None
                }
            )
        )

        repeated_event_count = self._count_repeated_events(records)
        anomaly_count = self._count_anomalies(records)

        return LearningPattern(
            pattern_id=f"event_type:{classification_key}",
            pattern_type="event_type",
            classification_key=classification_key,
            frequency=len(records),
            anomaly_count=anomaly_count,
            repeated_event_count=repeated_event_count,
            source_key=source_key,
            first_seen=first_seen,
            last_seen=last_seen,
            schema_versions=schema_versions,
            metadata={
                "record_count": len(records),
            },
        )

    def _record_timestamp(
        self,
        record: Any,
    ) -> Optional[datetime]:

        if hasattr(record, "timestamp"):
            return getattr(record, "timestamp")

        if isinstance(record, dict):
            return record.get("timestamp")

        return None

    def _record_schema_version(
        self,
        record: Any,
    ) -> Optional[str]:

        if hasattr(record, "schema_version"):
            return getattr(record, "schema_version")

        if isinstance(record, dict):
            value = record.get("schema_version")
            if isinstance(value, str):
                return value

        return None

    def _record_event_id(
        self,
        record: Any,
    ) -> Optional[str]:

        if hasattr(record, "event_id"):
            return getattr(record, "event_id")

        if isinstance(record, dict):
            return record.get("event_id")

        return None

    def _count_repeated_events(
        self,
        records: Sequence[Any],
    ) -> int:

        event_ids = [
            event_id
            for record in records
            if (event_id := self._record_event_id(record)) is not None
        ]
        counter = Counter(event_ids)
        return sum(count - 1 for count in counter.values() if count > 1)

    def _count_anomalies(
        self,
        records: Sequence[Any],
    ) -> int:

        anomalies = 0

        for record in records:
            if self._record_timestamp(record) is None:
                anomalies += 1
            if self._record_event_id(record) is None:
                anomalies += 1

        return anomalies
