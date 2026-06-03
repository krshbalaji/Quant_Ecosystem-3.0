PACK214 Design Review
=====================

Branch: `release/qe3-v1-institutional`
Baseline: `689 passed`

Input
-----
- `PACK214_AUDIT_REPLAY_SPEC.md`

Review Scope
------------
- Query Model
- Replay Engine
- Safety Rules
- Result Contract
- Performance
- Forward Compatibility

Strengths
---------
- The spec clearly separates the query layer from the replay layer.
- Query model supports direct `key`, lineage, namespace, topology, timestamp, schema version, and pagination filters.
- Safety rules are explicit and conservative: replay is read-only, non-executing, and non-governance.
- Replay result shape is well-defined with `source_key`, timestamps, `status`, `issues`, and `records`.
- Performance expectations correctly acknowledge current `MultiMapStore` limitations and recommend future streaming/chunking.
- Forward compatibility is addressed by schema version metadata and a conservative mismatch failure mode.

Risks
-----
- `MultiMapStore` is in-memory and not durable; replay architecture risks being tightly coupled to a non-production store.
- The current key model is narrow: only three concrete audit keys are implemented today, leaving `namespace` and `topology` lookup semantics only partially grounded.
- Pagination is described as slicing full list results, which can become costly for large histories and may not scale without storage-level support.
- `event_type` and payload-level filtering are proposed, but there is no explicit guarantee that audit records will carry the necessary fields.
- The spec does not mandate a strong metadata contract for every persisted audit record, leaving `schema_version`, `event_id`, and `timestamp` implicit rather than enforced.

Missing Capabilities
--------------------
- No explicit query key pattern for `audit.namespace.<namespace>` or `audit.topology.<namespace>` beyond the registry key.
- No direct support for partial/streaming reads from `MultiMapStore`.
- No mechanism for cross-key lineage discovery beyond exact `lineage_id` or registry lookup.
- No explicit audit index or metadata catalog in the spec to support query planning.
- No clear contract for audit payload contents, such as `sequence_number`, `source`, and `schema_version` fields on every record.

Recommended Changes
-------------------
1. Define a canonical audit metadata contract for persisted records:
   - require `event_id`, `timestamp`, `schema_version`, and optional `sequence_number` on all audit items.
2. Clarify namespace filtering semantics:
   - specify whether `namespace` maps only to `audit.topology.namespace_registry` or also to `audit.namespace.<namespace>`.
3. Add explicit key patterns for support domains beyond lineage:
   - `audit.execution.outcome.<instrument_or_lineage_id>`
   - `audit.federation.dispatch.<event_type>`
   - `audit.governance.decision.<decision_id>`
4. Tighten pagination guidance:
   - document that current implementation is limited to list slicing and that future durable stores are required for large replay workloads.
5. Add a catalog of supported query filters and their expected payload fields.
6. Introduce a replay safety assurance statement that `legacy_read_status` is optional and if present must remain diagnostic-only.

Approval Recommendation
-----------------------
- Recommend conditional approval of the spec as an architecture design document.
- Approval should be granted if the next phase incorporates the recommended metadata contract and stronger namespace/key semantics.
- The spec is fit for Phase 107 planning, but it must be refined before implementation to avoid coupling replay to in-memory store assumptions.

Summary
-------
The PACK214 design is a solid first draft for audit replay architecture. It correctly emphasizes read-only safety, key-based query resolution, and schema version awareness.
However, it needs tighter metadata and key semantics, plus a more explicit handling of large-history pagination and durability risk, before moving to implementation.
