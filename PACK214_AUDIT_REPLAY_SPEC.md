PACK214 Audit Replay Specification
===================================

Branch: `release/qe3-v1-institutional`
Baseline: `689 passed`

Purpose
-------
Define the architecture for audit replay using the current Phase 106 foundation.
This document is specification-only: no code, no migrations, no implementation.

Foundations
-----------
The replay design builds on the following existing capabilities:
- `MultiMapStore`: minimal in-memory append-only store with `put`, `get`, `latest`, `keys`, `size`
- Audit Persistence Foundation: shadow-only audit writes with canonical `audit.*` keys
- `MemoryLineage` and `ExecutionLineage`: legacy lineage models with shadow persistence into `MultiMapStore`
- `EventBus`: in-process publish/subscribe foundation
- `MemoryEventAdapter`: adapter that captures raw events into `MultiMapStore`

Current Audit Persistence Keys
------------------------------
The repository currently uses these audit key patterns:
- `audit.execution.lineage.<lineage_id>`
  - ordered lineage snapshots and execution artifacts
- `audit.execution.lineage_registry`
  - registry of known lineage IDs appended by `FederationAuditRegistry`
- `audit.topology.namespace_registry`
  - topology audit snapshots appended by `FederationNamespaceAuditor`

The spec also reserves logical audit key families for future use:
- `audit.execution.outcome.<instrument_or_lineage_id>`
- `audit.federation.dispatch.<event_type>`
- `audit.namespace.<namespace>`
- `audit.governance.decision.<decision_id>`

MultiMapStore Storage Patterns
------------------------------
- `MultiMapStore` is currently an in-memory `Dict[str, List[Any]]`.
- Values are appended with `put(key, value)` and read with `get(key)`.
- `latest(key)` is a convenience read for the most recent item.
- There is no current support for partial reads, indexing beyond key names, or durable persistence.
- Current storage pattern is append-only shadow persistence without legacy read-path changes.

Existing Audit-Related Registries
---------------------------------
- `FederationAuditRegistry`: tracks `ExecutionLineage` instances and appends lineage IDs to `audit.execution.lineage_registry`.
- `FederationNamespaceAuditor`: evaluates `NamespaceRegistry` and appends a `TopologyAuditResult` to `audit.topology.namespace_registry`.

Existing Lineage Models
-----------------------
- `ExecutionLineage`:
  - primary legacy lineage is stored in `events`
  - shadow persistence writes each appended audit event into `audit.execution.lineage.<lineage_id>`
- `MemoryLineage`:
  - legacy lineage snapshots are stored in `_lineages`
  - shadow persistence writes each appended snapshot into `audit.execution.lineage.<lineage_id>`

Audit Replay Requirements
-------------------------
The replay subsystem must satisfy these requirements:
- Replay is read-only and diagnostic-only.
- Legacy storage remains authoritative for production behavior.
- Replay must be able to reconstruct ordered event sequences from audit shadow keys.
- Replay must expose lineage, namespace, and topology query filters.
- Replay must detect gaps, ordering anomalies, and schema/version mismatches.
- Replay must avoid any execution, routing, or governance side effects.
- Replay result objects must include metadata for source key, timestamps, and summary.

A. Query Model
--------------
The query model is a declarative read layer over audit keys.

AuditReplayQuery
~~~~~~~~~~~~~~~~
A single query object should support:
- `key`: optional exact audit key
- `lineage_id`: optional lineage identifier
- `namespace`: optional topology namespace or registry namespace
- `event_type`: optional event payload type filter
- `schema_version`: optional schema version filter
- `timestamp_range`: optional start/end time window
- `limit`: optional maximum number of records
- `offset`: optional offset for pagination

Query Filters
~~~~~~~~~~~~~
- `lineage filters`
  - `lineage_id` selects `audit.execution.lineage.<lineage_id>`.
  - `lineage_id` may also derive from registry keys if key is absent.
- `namespace filters`
  - `namespace` selects keys such as `audit.topology.<namespace>` or `audit.namespace.<namespace>`.
- `topology filters`
  - topology queries may target `audit.topology.namespace_registry` and apply payload-level filters.
- `payload filters`
  - support item-level filtering by `event_id`, `sequence_number`, `schema_version`, or `source`.

Query semantics
~~~~~~~~~~~~~~~
- If `key` is provided, query resolves directly against `MultiMapStore.get(key)`.
- If `lineage_id` is provided without `key`, query computes `audit.execution.lineage.<lineage_id>`.
- If `namespace` is provided, query maps to relevant audit topology keys.
- If no direct key is available, query resolves via derived index keys or registry lookups.

B. Replay Model
---------------
The replay model defines how audit sequences are validated and represented.

AuditReplayEngine
~~~~~~~~~~~~~~~~~
The engine is a read-only component with responsibilities:
- resolve audit keys for a replay request
- load ordered audit values from `MultiMapStore`
- validate sequence continuity and monotonic timestamps
- enforce schema version compatibility
- produce a replay result object

AuditReplayResult
~~~~~~~~~~~~~~~~~
The result should include:
- `query`: the original `AuditReplayQuery`
- `source_key`: the audit key used for replay
- `record_count`: number of items replayed
- `first_timestamp` / `last_timestamp`
- `schema_versions`: versions encountered
- `status`: e.g. `OK`, `GAP_DETECTED`, `SCHEMA_MISMATCH`, `EMPTY`
- `issues`: list of warnings/errors found during replay
- `records`: replayed audit items or a reference to them

Replay validation rules
~~~~~~~~~~~~~~~~~~~~~~~
- `GAP_DETECTED` if sequence numbers or timestamps are not strictly monotonic.
- `SCHEMA_MISMATCH` if a record has an unsupported `schema_version`.
- `DUPLICATE_EVENT` if identical `event_id` appears more than once in the same audit sequence.
- `SOURCE_MISMATCH` if source metadata differs from expected lineage origin.

C. Lookup Strategy
------------------
The lookup strategy defines how `MultiMapStore` keys are resolved and consumed.

MultiMapStore Access Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Prefer direct key reads via `get(key)` for known audit paths.
- Use `latest(key)` only for last-record diagnostics, not full replay.
- Avoid broad `keys()` scans for production replay; only use scans in controlled diagnostics.

Key Resolution Strategy
~~~~~~~~~~~~~~~~~~~~~~~
- Primary resolution paths:
  - `lineage_id` → `audit.execution.lineage.<lineage_id>`
  - `registry` → `audit.execution.lineage_registry`
  - `namespace` → `audit.topology.namespace_registry`
- Derived index keys may be introduced later as:
  - `index.audit.lineage.by_namespace.<namespace>`
  - `index.audit.lineage.by_event_type.<event_type>`
- The engine should support a fallback strategy:
  - first resolve direct key
  - then resolve via registry or index if direct key is unavailable

Pagination Strategy
~~~~~~~~~~~~~~~~~~~
- `MultiMapStore` returns full lists today; the replay layer must wrap results with pagination metadata.
- Pagination may be implemented in the replay layer by slicing the returned list:
  - `offset` and `limit`
- For large histories, prefer designing a chunked or streaming read API in future phases.
- The spec should document that current lookup complexity is O(n) on list size, with no native partial retrieval support.

D. Safety Rules
----------------
Replay must be strictly non-invasive.
- replay is read-only: no writes to legacy or audit stores
- no execution of business logic, side effects, or command issuance
- no routing through event buses or runtime workflow paths
- no governance actions, state changes, or cutover decisions
- replay should operate in a sandboxed diagnostics mode only

E. Versioning
---------------
The replay subsystem must support schema version metadata.

Schema Version Support
~~~~~~~~~~~~~~~~~~~~~~
- Audit records must carry `schema_version` when persisted.
- Replay must read version metadata from each record.
- The replay engine should accept an `allowed_schema_versions` set.
- If a record has an unsupported version, the engine returns `SCHEMA_MISMATCH`.

Forward Compatibility
~~~~~~~~~~~~~~~~~~~~~
- design the replay model so it can tolerate newer versions by:
  - preserving raw record payloads in results
  - surfacing unrecognized fields rather than failing immediately when safe
- if forward compatibility cannot be guaranteed, replay should fail with a clear mismatch status.

F. Result Format
----------------
Audit replay results should be structured and machine-friendly.

Core result fields
~~~~~~~~~~~~~~~~~~
- `query`: serialized audit query parameters
- `source_key`: canonical `MultiMapStore` key used
- `record_count`: number of records included
- `first_timestamp`, `last_timestamp`
- `status`
- `issues`: validation warnings/errors
- `schema_versions`: encountered versions
- `records`: the replay items

Additional metadata
~~~~~~~~~~~~~~~~~~~
- `resolution_path`: how the key was resolved (direct key, registry lookup, index lookup)
- `replay_duration_ms`: time taken to execute the replay
- `data_size`: estimated size of returned payloads
- `legacy_read_status`: if optional cross-check is performed against legacy lineage, include parity result

G. Performance Expectations
---------------------------
The architecture should set conservative expectations for the current in-memory store.

Lookup complexity
~~~~~~~~~~~~~~~~~
- Key resolution is O(1) for direct key lookups.
- Record retrieval is O(n) in the number of items stored under that key.
- Current replay filtering and pagination are O(n) because `MultiMapStore` returns full lists.

Large-history handling
~~~~~~~~~~~~~~~~~~~~~~
- Large lineage histories will degrade replay performance linearly.
- The spec must recommend limiting replay batch sizes and adding explicit `limit`/`offset` support.
- For long-lived audit histories, the next phase should include:
  - chunked storage
  - streaming read semantics
  - durable backing store with partial retrieval

Implementation notes
---------------------
- Keep replay mechanics separate from `EventBus`, `MemoryEventAdapter`, and governance paths.
- Reuse existing audit key naming conventions from Phase 106.
- The audit replay layer should act as a monitoring/diagnostic service on top of `MultiMapStore`.

Non-goals
----------
- This spec does not authorize using replay as a production execution path.
- It does not require changing legacy `MemoryLineage` or `ExecutionLineage` reads.
- It does not define durable storage beyond the current `MultiMapStore` shadow layer.
- It does not prescribe a specific user interface or API surface.

Next steps
----------
- Approve the audit replay query and replay models.
- Define a small set of canonical replay keys and derived indexes for future implementation.
- Validate the replay result format against representative audit records.
