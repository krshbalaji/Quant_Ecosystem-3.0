**PACK213 Audit Persistence Spec**

**Purpose:**
- **Goal:** Define a safe, shadow-mode persistence design to capture federation/audit artifacts (registry entries, dispatch records, topology audits, and execution lineage) into `MultiMapStore` for forensic queries, replay, and eventual migration.
- **Constraints:** No production behavior changes; append-only shadow writes only; legacy storage remains authoritative for reads until explicit cutover.

**Scope:**
- Components analyzed: `FederationAuditRegistry`, `FederationTopologyAuditEngine`, `FederationNamespaceAuditor`, `ExecutionLineage`.
- Deliverable: key strategy, shadow persistence rules, query patterns, replay and rollback approaches.

**1. MultiMapStore Key Strategy**
- **Principles:** human-readable, hierarchical keys; single-purpose per key; include namespace and type; support efficient list retrieval and `latest()` semantics.
- **Recommended key patterns:**
  - **Execution lineage records:** `audit.execution.lineage.<lineage_id>` → ordered list of lineage entries (append-only)
  - **Execution outcomes:** `audit.execution.outcome.<instrument or lineage_id>` → list of outcome events
  - **Federation dispatch records:** `audit.federation.dispatch.<event_type>` → list of EventDispatchRecord
  - **Topology audits:** `audit.topology.<namespace>` → list of TopologyAuditResult snapshots
  - **Namespace audit events:** `audit.namespace.<namespace>` → list of namespace-level audit events
  - **Governance decisions (audit):** `audit.governance.decision.<decision_id or request_id>` → list of decision records
  - **Derived indexes (optional):** `index.execution.by_adapter.<adapter_id>` or `index.federation.by_subscriber.<subscriber_id>` to enable cross-key queries without scanning all keys
- **Key metadata guidance:** store canonical event object that includes `event_id`, `timestamp` (ISO-8601), `source`, and `schema_version` fields to enable evolution and idempotency.

**2. Shadow Persistence Strategy**
- **Write model:** mirror writes — when a component produces an artifact (e.g., `ExecutionLineage.register()`), perform the legacy write first (unchanged), then perform a best-effort append to `MultiMapStore` under the canonical key.
- **Failure semantics:** adapter must swallow persistence errors and never raise to caller (shadow-only); log error telemetry for operational visibility.
- **Idempotency:** include `event_id` and sequence numbers in objects; when appending, check latest item's `event_id` to avoid duplicate re-append within the same process lifetime. (For in-memory `MultiMapStore`, de-dup at append time if last entry matches `event_id`.)
- **Ordering:** preserve original append order (use existing timestamps or sequence numbers); shadow appends should occur immediately after legacy write to avoid race windows.
- **Atomicity:** do not attempt cross-store transactions. Treat shadow persistence as eventual consistency with strong ordering guarantees within process boundary.
- **Backfill and reconciliation:** provide a reconciliation worker to scan legacy sources and ensure missing artifacts are populated into `MultiMapStore` (see Replay Strategy).
- **Privacy & PII:** ensure audit payloads are reviewed for PII; apply redaction at adapter boundary when necessary.

**3. Query Strategy**
- **Primary primitives:** `get(key)`, `latest(key)`, `keys()` and `size()` already available on `MultiMapStore`.
- **Common query patterns:**
  - Retrieve full lineage: `get('audit.execution.lineage.<lineage_id>')` → used for replay
  - Latest outcome for an instrument: `latest('audit.execution.outcome.<instrument>')`
  - Dispatch records by event type: `get('audit.federation.dispatch.<event_type>')`
  - Topology snapshot history: `get('audit.topology.<namespace>')`
- **Indexing approach:** avoid global scans by maintaining small derived keys that act as lightweight indexes. For example, create keys like `index.lineage.by_instrument.<instrument>` that list `lineage_id`s when new lineage created. Keep indexes append-only and light-weight.
- **Pagination & filtering:** since `MultiMapStore` is in-memory and returns full lists, provide query helpers that perform server-side filtering (by timestamp range, event_id, or sequence ranges) and support streaming through generator helpers for large datasets.
- **Retention & pruning:** implement configurable retention policies (time-based or count-based) implemented by an offline retention worker; retention should be policy-driven and NOT auto-delete historic artifacts needed for compliance without explicit governance approval.
- **Observability:** emit telemetry counters for append, get, latest and reconciliation failures.

**4. Replay Strategy**
- **Purpose:** allow deterministic replay of execution history or topology changes for debugging, testing, and model retraining.
- **Source-of-truth:** until cutover, legacy storage remains authoritative for reads; `MultiMapStore` is the shadow snapshot store used for replay validation and diagnostics.
- **Replay harness design:**
  - A deterministic replay driver accepts a `lineage_id` or `instrument` and:
    - Reads ordered events from `audit.execution.lineage.<lineage_id>` (shadow store)
    - Optionally cross-checks sequence/timestamps against legacy `ExecutionLineage` read to detect missing or divergent entries
    - Re-applies events into a sandboxed runner that implements idempotent apply semantics
  - Include preflight checks: schema version match, monotonic timestamps, and no-event gaps (sequence continuity). Fail fast on schema drift.
- **Reconciliation workflow:**
  - Periodically run a reconciliation job that compares legacy lineage counts to `MultiMapStore` counts and enqueues missing items for backfill using the legacy source as definitive.
  - Provide a reconciliation report that lists mismatches and suggested remediation steps.

**5. Rollback Strategy**
- **Principles:** avoid destructive operations; prefer feature-flag driven cutover that is reversible; maintain legacy behavior until promotion is explicit and validated.
- **Promotion (cutover) plan (high-level):**
  1. Deploy shadow persistence and run parity reconciliation until >99.9% parity for target datasets.
  2. Enable read-mirroring tests where the system reads both legacy and shadow stores, compares results, but continues using legacy outputs (compare-only mode).
  3. Introduce a staged consumer feature-flag that allows non-critical consumers to read from shadow for validation (non-authoritative).
  4. When metrics and audits show parity and stability, flip feature flag to allow selected subsystems to use shadow as primary after a brief monitoring window.
- **Rollback actions:**
  - If divergence or failures detected after promotion, toggle feature flag off to revert consumers to legacy reads immediately.
  - Run reconciliation to identify missing entries; use backfill to repopulate `MultiMapStore` from legacy; resume promotion testing when parity restored.
  - Do NOT delete shadow data; retain for forensic analysis.

**Operational Considerations & Validation**
- **Testing checklist:**
  - Unit tests for adapter append semantics (idempotency, ordering)
  - Parity tests that compare legacy reads vs. shadow contents for representative datasets
  - Reconciliation job tests for detection and backfill
  - Replay harness tests ensuring deterministic re-application
- **Monitoring & alerts:**
  - Alert on shadow append failures, parity drift > threshold, reconciliation error rate
  - Track append latency and size growth of keys
- **Security:**
  - Ensure persisted audit artifacts respect access control—restrict read/write access to audit data to authorized processes
  - Encrypt persisted payloads if they contain sensitive fields
- **Data retention policy:**
  - Default: retain audit artifacts for N days (configurable) and maintain a compliance retention mode for longer-term storage (export to durable store) under governance control

**Mapping: components → key examples**
- `ExecutionLineage` → `audit.execution.lineage.<lineage_id>` (list of lineage snapshots/events)
- `FederationAuditRegistry` → `audit.federation.lineage_registry` (index of lineage IDs) and `audit.execution.lineage.<lineage_id>` entries
- `FederationEventBus` dispatch records → `audit.federation.dispatch.<event_type>`
- `FederationTopologyAuditEngine` results → `audit.topology.<namespace>`

**Non-Goals / Warnings**
- This spec intentionally avoids recommending any change to legacy read-paths or execution semantics.
- Do not use `MultiMapStore` as a long-term durable store in its current in-memory form; plan for an export path to durable storage (object store or DB) for production compliance.

**Next steps**
- Review and approve key naming and retention policies.
- Implement Pack213 adapter (shadow-only) per the test harness and reconciliation plan.
- Schedule parity validation window (metric thresholds and acceptance criteria).

Prepared for PHASE106 PACK213 — Audit Persistence design.
