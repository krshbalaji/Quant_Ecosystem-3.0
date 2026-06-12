from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.cognition.swarm.audit_event import AuditEvent


AUDIT_REPLAY_STATUS_OK = "OK"
AUDIT_REPLAY_STATUS_NO_RECORDS = "NO_RECORDS"
AUDIT_REPLAY_STATUS_INVALID_QUERY = "INVALID_QUERY"
AUDIT_REPLAY_STATUS_SCHEMA_MISMATCH = "SCHEMA_MISMATCH"


@dataclass(frozen=True)
class AuditReplayQuery:
    key: Optional[str] = None
    lineage_id: Optional[str] = None
    namespace: Optional[str] = None
    topology_filter: Optional[str] = None
    event_type: Optional[str] = None
    timestamp_from: Optional[datetime] = None
    timestamp_to: Optional[datetime] = None
    schema_version: Optional[str] = None
    limit: Optional[int] = None
    offset: int = 0


@dataclass
class AuditReplayResult:
    query: AuditReplayQuery
    source_key: Optional[str]
    record_count: int
    first_timestamp: Optional[datetime]
    last_timestamp: Optional[datetime]
    schema_versions: List[str]
    status: str
    issues: List[str] = field(default_factory=list)
    records: List[Any] = field(default_factory=list)


class AuditReplayEngine:

    def __init__(self, store: MultiMapStore) -> None:
        self._store = store

    def replay(self, query: AuditReplayQuery) -> AuditReplayResult:
        resolved_keys, issues = self._resolve_source_keys(query)
        if not resolved_keys:
            status = AUDIT_REPLAY_STATUS_INVALID_QUERY
            if query.key or query.lineage_id or query.namespace or query.topology_filter:
                status = AUDIT_REPLAY_STATUS_NO_RECORDS
            return AuditReplayResult(
                query=query,
                source_key=None,
                record_count=0,
                first_timestamp=None,
                last_timestamp=None,
                schema_versions=[],
                status=status,
                issues=issues,
                records=[],
            )

        source_key = resolved_keys[0] if len(resolved_keys) == 1 else ", ".join(resolved_keys)
        records = self._load_records(resolved_keys)
        filtered_records = self._apply_filters(records, query, resolved_keys, issues)

        timestamps = [self._record_timestamp(record) for record in filtered_records]
        timestamps = [ts for ts in timestamps if ts is not None]

        schema_versions = self._unique_schema_versions(filtered_records)
        status = AUDIT_REPLAY_STATUS_OK if filtered_records else AUDIT_REPLAY_STATUS_NO_RECORDS

        return AuditReplayResult(
            query=query,
            source_key=source_key,
            record_count=len(filtered_records),
            first_timestamp=min(timestamps) if timestamps else None,
            last_timestamp=max(timestamps) if timestamps else None,
            schema_versions=schema_versions,
            status=status,
            issues=issues,
            records=filtered_records,
        )

    from typing import List, Tuple
    def _resolve_source_keys(
        self,
        query: AuditReplayQuery,
    ) -> tuple[List[str], List[str]]:
        keys: List[str] = []
        issues: List[str] = []

        if query.key:
            if query.key in self._store.keys():
                keys.append(query.key)
            else:
                issues.append("KEY_NOT_FOUND")
            return keys, issues

        if query.lineage_id:
            lineage_key = f"audit.execution.lineage.{query.lineage_id}"
            if lineage_key in self._store.keys():
                keys.append(lineage_key)
            else:
                issues.append("LINEAGE_NOT_FOUND")

        if query.namespace:
            namespace_key = f"audit.namespace.{query.namespace}"
            if namespace_key in self._store.keys():
                keys.append(namespace_key)
            else:
                matched = [k for k in self._store.keys() if query.namespace in k]
                if matched:
                    keys.extend(matched)
                else:
                    issues.append("NAMESPACE_NOT_FOUND")

        if query.topology_filter:
            topology_keys = [k for k in self._store.keys() if "audit.topology." in k]
            if topology_keys:
                keys.extend(topology_keys)
            else:
                issues.append("TOPOLOGY_NOT_FOUND")

        # preserve deterministic order and uniqueness
        unique_keys: List[str] = []
        for key in keys:
            if key not in unique_keys:
                unique_keys.append(key)

        return unique_keys, issues

    def _load_records(self, keys: Sequence[str]) -> List[Any]:
        records: List[Any] = []
        for key in keys:
            records.extend(self._store.get(key))
        return records

    def _apply_filters(
        self,
        records: Sequence[Any],
        query: AuditReplayQuery,
        resolved_keys: Sequence[str],
        issues: List[str],
    ) -> List[Any]:
        filtered = list(records)

        if query.event_type is not None:
            filtered = [r for r in filtered if getattr(r, "event_type", None) == query.event_type]

        if query.schema_version is not None:
            filtered = [r for r in filtered if self._record_schema_version(r) == query.schema_version]
            if not filtered:
                issues.append("SCHEMA_MISMATCH")

        if query.timestamp_from is not None:
            tmp: List[Any] = []

            for r in filtered:
                ts = self._record_timestamp(r)

                if ts is not None and ts >= query.timestamp_from:
                    tmp.append(r)

            filtered = tmp
            
        if query.timestamp_to is not None:
            tmp: List[Any] = []

            for r in filtered:
                ts = self._record_timestamp(r)

                if ts is not None and ts <= query.timestamp_to:
                    tmp.append(r)

            filtered = tmp

        if query.namespace is not None:
            filtered = [
                r for r in filtered
                if getattr(r, "namespace", None) == query.namespace
                or (isinstance(r, dict) and r.get("namespace") == query.namespace)
            ]

        if query.topology_filter is not None:
            filtered = [
                r for r in filtered
                if "topology" in getattr(r, "__class__", type(r)).__name__.lower()
                or "topology" in resolved_keys[0]
            ]

        if query.offset:
            filtered = filtered[query.offset:]

        if query.limit is not None:
            filtered = filtered[: query.limit]

        return filtered

    def _record_timestamp(self, record: Any) -> Optional[datetime]:
        if hasattr(record, "timestamp"):
            return getattr(record, "timestamp")
        if isinstance(record, dict):
            return record.get("timestamp")
        return None

    def _record_schema_version(self, record: Any) -> Optional[str]:
        if hasattr(record, "schema_version"):
            return getattr(record, "schema_version")
        if isinstance(record, dict):
            value = record.get("schema_version")
            if isinstance(value, str):
                return value
        return None

    def _unique_schema_versions(self, records: Sequence[Any]) -> List[str]:
        versions = [version for version in (self._record_schema_version(r) for r in records) if version is not None]
        return sorted(set(versions))
