from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from quant_ecosystem.core.multimap_store import MultiMapStore

from .knowledge_pattern import KnowledgePattern


KNOWLEDGE_REPLAY_STATUS_OK = "OK"
KNOWLEDGE_REPLAY_STATUS_NO_RECORDS = "NO_RECORDS"
KNOWLEDGE_REPLAY_STATUS_INVALID_QUERY = "INVALID_QUERY"
KNOWLEDGE_REPLAY_STATUS_NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class KnowledgeReplayQuery:
    key: Optional[str] = None
    pattern_id: Optional[str] = None
    category: Optional[str] = None
    pattern_type: Optional[str] = None
    source_key: Optional[str] = None
    lineage_id: Optional[str] = None
    provenance: Optional[str] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None
    limit: Optional[int] = None
    offset: int = 0


@dataclass
class KnowledgeReplayResult:
    query: KnowledgeReplayQuery
    source_keys: List[str]
    record_count: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    schema_versions: List[str]
    status: str
    issues: List[str] = field(default_factory=list)
    records: List[KnowledgePattern] = field(default_factory=list)


class KnowledgeReplayEngine:

    def __init__(self, store: MultiMapStore) -> None:
        self._store = store

    def replay(self, query: KnowledgeReplayQuery) -> KnowledgeReplayResult:
        resolved_keys, issues = self._resolve_source_keys(query)
        if not resolved_keys:
            status = KNOWLEDGE_REPLAY_STATUS_INVALID_QUERY
            if any([query.key, query.pattern_id, query.category, query.source_key, query.lineage_id, query.provenance]):
                status = KNOWLEDGE_REPLAY_STATUS_NO_RECORDS
            return KnowledgeReplayResult(
                query=query,
                source_keys=[],
                record_count=0,
                first_seen=None,
                last_seen=None,
                schema_versions=[],
                status=status,
                issues=issues,
                records=[],
            )

        keyed_patterns = self._load_patterns_with_keys(resolved_keys)
        patterns = [pattern for _, pattern in keyed_patterns]
        filtered = self._apply_filters(patterns, query, resolved_keys, issues)

        timestamps = [pattern.first_seen for pattern in filtered if pattern.first_seen is not None]
        timestamps.extend([pattern.last_seen for pattern in filtered if pattern.last_seen is not None])
        timestamps = [ts for ts in timestamps if ts is not None]

        schema_versions = sorted({version for pattern in filtered for version in pattern.schema_versions})
        status = KNOWLEDGE_REPLAY_STATUS_OK if filtered else KNOWLEDGE_REPLAY_STATUS_NO_RECORDS

        filtered_keys: List[str] = []
        for key, pattern in keyed_patterns:
            if pattern in filtered and key not in filtered_keys:
                filtered_keys.append(key)

        return KnowledgeReplayResult(
            query=query,
            source_keys=filtered_keys,
            record_count=len(filtered),
            first_seen=min(timestamps) if timestamps else None,
            last_seen=max(timestamps) if timestamps else None,
            schema_versions=schema_versions,
            status=status,
            issues=issues,
            records=filtered,
        )

    def _resolve_source_keys(self, query: KnowledgeReplayQuery) -> (List[str], List[str]):
        keys: List[str] = []
        issues: List[str] = []
        available = [key for key in self._store.keys() if key.startswith("audit.learning.pattern.")]

        if query.key:
            if query.key in available:
                keys.append(query.key)
            else:
                issues.append("KEY_NOT_FOUND")
            return keys, issues

        any_filter = any(
            [
                query.pattern_id,
                query.category,
                query.pattern_type,
                query.source_key,
                query.lineage_id,
                query.provenance,
            ]
        )

        if any_filter:
            return available, issues

        return [], issues

    def _load_patterns_with_keys(self, keys: Sequence[str]) -> List[tuple]:
        keyed_patterns: List[tuple] = []
        for key in keys:
            for pattern in self._store.get(key):
                keyed_patterns.append((key, pattern))
        return keyed_patterns

    def _apply_filters(
        self,
        patterns: Sequence[KnowledgePattern],
        query: KnowledgeReplayQuery,
        resolved_keys: Sequence[str],
        issues: List[str],
    ) -> List[KnowledgePattern]:
        filtered = list(patterns)

        if query.pattern_id is not None:
            filtered = [p for p in filtered if p.pattern_id == query.pattern_id]

        if query.category is not None:
            filtered = [p for p in filtered if p.category == query.category]

        if query.pattern_type is not None:
            filtered = [p for p in filtered if p.pattern_type == query.pattern_type]

        if query.source_key is not None:
            filtered = [p for p in filtered if query.source_key in p.source_keys]

        if query.lineage_id is not None:
            filtered = [p for p in filtered if any(query.lineage_id in key for key in p.source_keys)]

        if query.provenance is not None:
            filtered = [p for p in filtered if any(query.provenance in prov for prov in p.provenance)]

        if query.timestamp_from is not None:
            filtered = [p for p in filtered if p.first_seen is not None and p.first_seen >= query.timestamp_from]

        if query.timestamp_to is not None:
            filtered = [p for p in filtered if p.last_seen is not None and p.last_seen <= query.timestamp_to]

        if query.offset:
            filtered = filtered[query.offset:]

        if query.limit is not None:
            filtered = filtered[: query.limit]

        return filtered

    def _serialize_key(self, key: str) -> str:
        return key
