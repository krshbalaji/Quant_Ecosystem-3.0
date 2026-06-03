PACK214 Implementation Guardrails
================================

Branch: `release/qe3-v1-institutional`
Baseline: `689 passed`

Purpose
-------
Define architecture governance guardrails for implementing audit replay support in Phase 107.
This document is architecture-only: no code, no migrations, no implementation.

1. Naming Standard
------------------
- Use canonical `.` separators in audit keys.
- All audit replay keys must begin with `audit.`.
- Preferred key families:
  - `audit.execution.lineage.<lineage_id>`
  - `audit.execution.lineage_registry`
  - `audit.topology.namespace_registry`
  - future keys: `audit.namespace.<namespace>`, `audit.execution.outcome.<instrument_or_lineage_id>`, `audit.governance.decision.<decision_id>`
- Use stable identifiers for lineage, namespace, and decision keys.

2. Query Standard
-----------------
- Support a declarative `AuditReplayQuery` object.
- Required query filters:
  - `key` (exact audit key)
  - `lineage_id`
  - `namespace`
  - `event_type`
  - `schema_version`
  - `timestamp_range`
  - `limit` and `offset`
- Establish lookup precedence:
  1. exact `key`
  2. derived `audit.execution.lineage.<lineage_id>`
  3. registry or index lookup
- Document that current filtering is performed in the replay layer over the full list returned by `MultiMapStore`.

3. Replay Standard
------------------
- Implement an `AuditReplayEngine` that resolves keys, loads ordered records, validates continuity, and emits structured `AuditReplayResult`.
- Replay must be deterministic and reproducible for the same query and source data.
- Replay engine results must include:
  - `query`
  - `source_key`
  - `record_count`
  - `first_timestamp`
  - `last_timestamp`
  - `schema_versions`
  - `status`
  - `issues`
  - `records`
- If replay validation detects gaps, duplicates, or version mismatches, the result must record those issues without changing state.

4. Versioning Standard
----------------------
- Persisted audit records must include `schema_version`.
- The replay engine must accept an `allowed_schema_versions` set.
- Unsupported versions must result in a clear `SCHEMA_MISMATCH` status.
- Forward compatibility should preserve raw record payloads and surface unknown fields safely.
- Future schema evolution must be handled via versioned transformation rules, not by mutating stored audit records in-place.

5. Rollback Standard
--------------------
- Replay is diagnostic-only; rollback actions are out-of-scope for the replay layer itself.
- The implementation must not introduce any governance, feature-flag, or read-path rollback logic in replay.
- If replay indicates a problem, the issue is surfaced to governance/operations, but no automated rollback is triggered from the replay engine.

6. Safety Standard
------------------
- Replay must be strictly read-only.
- Replay must not execute business actions, issue commands, or mutate application state.
- Replay must not publish events to `EventBus`.
- Replay must not trigger routing or governance decisions.
- Replay must not mutate `MultiMapStore` or legacy lineage models.
- Any optional legacy parity check must remain non-invasive and diagnostic-only.

7. Performance Standard
-----------------------
- Current `MultiMapStore` lookups are O(1) for key resolution and O(n) for record retrieval.
- Pagination is implemented by slicing full record lists; this is acceptable only as a temporary guardrail.
- Large history handling must be explicitly labeled as a future enhancement requiring chunked storage or streaming reads.
- The replay guardrail must include a warning that `keys()` scans are only for diagnostics, not normal replay.

8. Future Evolution Standard
----------------------------
- The replay architecture must remain extensible for additional audit domains:
  - governance replay
  - learning replay
  - federation replay
- Future domains must follow the same `audit.*` key naming and metadata contract.
- Support for derived index keys is encouraged to enable cross-domain query resolution.
- The replay layer should remain a diagnostic service, not a production execution path.

Non-goals
---------
- No code or implementation details are mandated here.
- No changes to legacy read-paths are authorized.
- No new EventBus routing or governance behavior is introduced.
- No durable storage or migration strategy is specified beyond current in-memory audit shadow store assumptions.
