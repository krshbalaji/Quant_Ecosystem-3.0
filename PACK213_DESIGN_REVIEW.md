PACK213 Design Review
=====================

Scope: review of PACK213_AUDIT_PERSISTENCE_SPEC.md focusing on key naming, retention, replay, shadow persistence, and rollback.

1) Key naming consistency
- Review: Proposed key patterns are clear and hierarchical (e.g., `audit.execution.lineage.<lineage_id>`).
- Validation: Keys consistently use `audit.` prefix, component domain, and specific identifier.
- Recommendation: Formalize a small key naming table and a single canonical separator policy (use `.` as proposed). Example additions:
  - Clarify whether `lineage_id` uses UUID vs human id; recommend UUID v4 (stable, globally unique).
  - Normalize index keys to a standard prefix: `index.*` (already suggested); recommend `index.audit.` to group indexes.

2) Retention policy
- Review: Spec suggests configurable retention and policy-driven pruning but left retention defaults unspecified.
- Ambiguities:
  - No default retention duration (e.g., 90/365 days) provided.
  - No explicit archive/export flow to durable storage for compliance-grade retention.
- Recommendations:
  - Define baseline defaults: short-term debugging retain 90 days; compliance mode (export) retain 7+ years (exported to durable, immutable storage).
  - Specify retention enforcement process and roles (who approves deletion/archival).
  - Add an export path to durable storage (S3/GCS) before any destructive pruning.

3) Replay policy
- Review: Replay harness and reconciliation process are well-defined; preflight checks (schema, monotonic timestamps) included.
- Missing edge cases:
  - Handling of partial lineage (mid-sequence gaps) during replay—spec suggests detection but not remediation steps beyond fail-fast.
  - Schema evolution handling: how to handle old schema versions during replay (migration, transformation, or reject).
- Recommendations:
  - Add remediation strategies for gaps: (a) auto-backfill via legacy read; (b) pause replay and surface manual reconciliation ticket.
  - Define schema migration rules: embedded `schema_version` per record plus transformation functions in the replay harness.
  - Provide replay idempotency guarantees: require event ids and replay offsets to allow resumable replays.

4) Shadow persistence policy
- Review: Shadow writes are non-blocking and swallow errors—this preserves runtime safety.
- Ambiguities / Edge cases:
  - De-duplication rule is only "compare latest event_id" — this fails if appends are retried after intermediate concurrent writes.
  - No guidance for cross-process idempotency (e.g., multi-instance system where multiple processes attempt to shadow-append the same artifact).
- Recommendations:
  - Strengthen idempotency by including a short-lived in-memory dedupe cache plus per-key last-event_id check. For cross-process idempotency, include a compact dedupe token within the payload and rely on eventual reconciliation to eliminate duplicates.
  - For persistence failures, cap retries with exponential backoff; always surface telemetry with failure counts.
  - Consider adding an append-with-check RPC pattern in future if `MultiMapStore` is backed by durable store supporting conditional writes.

5) Rollback policy
- Review: Promotion/rollback steps are sound and conservative.
- Missing details:
  - No explicit automated rollback triggers or thresholds (e.g., parity drift > 0.1% triggers automatic rollback).
  - No explicit validation window durations (how long to monitor before promoting further).
- Recommendations:
  - Define concrete thresholds and SLOs: e.g., parity drift threshold 0.1% (configurable), allowable append failure rate <0.01% per hour.
  - Define monitoring window: 24–72 hours observing metrics prior to staged promotion.
  - Document operator rollback playbook with exact feature-flag toggles and commands.

6) Ambiguities summary
- Key identifier formats (UUID vs human-readable) not prescriptive.
- Retention defaults and archival/export flows not specified.
- Cross-process idempotency and concurrent append semantics under-specified.
- No concrete thresholds/metrics for promotion/rollback.

7) Missing edge cases
- Replay when legacy source itself has been pruned or differs (broken source-of-truth).
- Handling schema drift across long-term retained artifacts.
- Large-key explosion: unbounded growth for hot keys (e.g., `audit.federation.dispatch.<very_high_cardinality_event>`).

8) Future scaling concerns
- `MultiMapStore` is in-memory; for scale, plan export/ETL to durable, indexed store (time-series DB, object store with manifest, or light document DB) before relying on it for real operations.
- Index strategy: derived index keys proposed are helpful but may not scale if high-cardinality indexes are created ad-hoc. Introduce cardinality controls and sampling for high-frequency events.
- Query performance: as lists grow, `get(key)` returning full lists will become heavy; implement streaming/pagination or chunked backing store.
- Retention & storage costs: large volumes require automated export and cold storage options; estimate expected ingestion rates prior to extended retention.

9) Acceptance checklist (for Pack213 implementation phase)
- Key naming table approved and committed.
- Baseline retention defaults set and export path defined.
- Shadow persistence adapter implements idempotency primitives and logs failure metrics.
- Reconciliation job implemented and validated on representative dataset.
- Replay harness supports schema migration and resumable replay.
- Operator rollback thresholds and playbook documented.

10) Recommended next actions
- Approve naming and baseline retention numbers (quick decision: 90 days debug, export 7 years compliance).
- Add explicit schema migration policy (versioning contract + transformers).
- Prepare a short PR that implements adapters in shadow-mode and includes the reconciliation harness and tests.

Prepared PACK213 design review. 
