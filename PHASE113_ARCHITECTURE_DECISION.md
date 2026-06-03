PHASE113C - GOVERNANCE INTELLIGENCE ARCHITECTURE DECISION

Status: Approved
Decision date: 2026-06-03

## Final Decision

Pack224 should be **B) thin orchestration layer**.

Pack224 must compose existing governance intelligence capabilities into a read-only, in-process coordinator. It must not create a new foundation, engine, registry, store, durable export path, schema registry, backfill worker, or persistence behavior.

This is not "composition only" because a small coordinator is still needed to sequence graph construction, reasoning, replay reads, observation creation, summarization, and report assembly into one repeatable Pack224 workflow. It is not a "new foundation" because all core domain capabilities already exist and must remain the source of behavior.

## Exact Reusable Capabilities

1. Cross-domain reasoning
   - Reuse `CrossDomainReasoningEngine`.
   - Reusable behavior: deterministic chain construction, provenance aggregation, cross-domain chain detection, reasoning result summaries, explanation text, status/issues output.
   - Pack224 use: invoke it against existing graph and registry inputs for selected pattern ids.

2. Knowledge graph construction and traversal
   - Reuse `KnowledgeGraphEngine`.
   - Reusable behavior: graph construction from `KnowledgeRegistry`, dependency mapping, relationship discovery, lineage graph generation.
   - Pack224 use: build transient graph context for reasoning and reports.

3. Knowledge replay reads
   - Reuse `KnowledgeReplayEngine`.
   - Reusable behavior: filtered replay over `audit.learning.pattern.*` keys, schema version collection, issue reporting, record return.
   - Pack224 use: read existing learning artifacts for governance intelligence summaries.

4. Audit replay reads
   - Reuse `AuditReplayEngine`.
   - Reusable behavior: forensic replay over audit keys, lineage/namespace/topology lookup, event/schema/timestamp filters, issue codes.
   - Pack224 use: read execution-level evidence when governance reports need audit context.

5. Governance observations and summaries
   - Reuse `GovernanceObservabilityEngine`.
   - Reusable behavior: convert knowledge patterns into governance observations, trace origins, summarize observation evolution/status distributions.
   - Pack224 use: create transient observations and report summaries.

6. Existing in-memory registries as inputs only
   - Reuse `KnowledgeRegistry` and existing observability registry types where already required by engine APIs.
   - Reusable behavior: pattern lookup, listing, grouping, counts, observation aggregation.
   - Pack224 use: pass existing registries through orchestration; do not introduce new registry types.

7. Existing consolidation semantics as reference only
   - Reuse `KnowledgeConsolidationEngine` behavior only where objects are already available and no write is required.
   - Pack224 use: no calls that persist, mutate stores, or change retention behavior.

## Exact Missing Capabilities

The following are real missing capabilities but are explicitly out of scope for Pack224 under Phase113C constraints:

1. Durable audit export and archival
   - No S3/GCS/database export path exists for compliance-grade retention.
   - Pack224 action: defer.

2. Automated reconciliation and backfill
   - No worker exists to repair parity gaps or repopulate missing replay keys.
   - Pack224 action: produce read-only discrepancy reports only; no repair writes.

3. Central schema registry and migration transforms
   - Existing engines surface schema versions and mismatches, but no centralized registry or transformer exists.
   - Pack224 action: report schema-version distribution and mismatch issues only.

4. Cross-process idempotency and conditional append semantics
   - Existing dedupe is not sufficient for multi-instance append safety.
   - Pack224 action: no writes, so this remains deferred.

5. Scalable streaming/pagination for high-cardinality keys
   - Large-key query behavior remains a risk.
   - Pack224 action: bounded read limits and reporting disclaimers only.

6. Metrics exporters, alerting, and SLO thresholds
   - Existing issue lists and summaries are not an operational monitoring system.
   - Pack224 action: return/report counters in memory; no monitoring integration.

7. Governance decision enforcement linkage
   - No causal link from observations/reasoning to enforcement records or approvals exists.
   - Pack224 action: report intelligence only; no enforcement wiring.

8. Canonical deduplication across learning/consolidation artifacts
   - Overlap exists between learning, consolidation, graph, and replay responsibilities.
   - Pack224 action: avoid new artifact creation; report duplicate indicators if visible.

## Architecture Rationale

The Phase113 census shows that the core intelligence primitives already exist: graph construction, replay, reasoning, provenance, issue reporting, and governance observation summaries. The gap analysis and feasibility audit show that the missing pieces are mostly operational foundations: persistence durability, schema migration, reconciliation/backfill, scaling, monitoring, and enforcement linkage.

Those missing pieces would require new engines, registries, stores, or persistence changes. Phase113C explicitly forbids those. Therefore Pack224 should be limited to a thin read-only orchestrator that coordinates existing engines and returns/report aggregates without changing system state.

## Pack224 Boundary

Allowed:
- Read existing registries and stores through existing engine APIs.
- Build transient graph/reasoning/replay/observation results in memory.
- Produce deterministic markdown/JSON-like report objects or console/test outputs.
- Add tests for orchestration sequencing and read-only report generation.
- Add operator documentation describing limitations and follow-up work.

Forbidden:
- New engines.
- New registries.
- New stores.
- Durable export paths.
- Shadow persistence.
- Backfill writes.
- Schema registry implementation.
- Runtime behavior changes.
- Governance enforcement wiring.

## Expected Implementation Shape

Pack224 should introduce a small orchestration module or equivalent adapter that:

1. Selects existing knowledge patterns from `KnowledgeRegistry`.
2. Builds a transient graph with `KnowledgeGraphEngine`.
3. Runs `CrossDomainReasoningEngine` for selected pattern ids.
4. Reads learning/audit evidence with `KnowledgeReplayEngine` and `AuditReplayEngine`.
5. Creates transient governance observations with `GovernanceObservabilityEngine`.
6. Returns a read-only governance intelligence report containing reasoning summaries, replay issues, provenance, schema versions, duplicate-risk indicators, and observation summaries.

## Expected LOC

Expected Pack224 implementation LOC: **300-450 LOC**.

Expected breakdown:
- Thin orchestrator and result models: 140-200 LOC
- Read-only report assembly and bounded query helpers: 80-120 LOC
- Feature flags/config wiring for enablement and stage selection: 30-50 LOC
- Operator documentation: 40-80 LOC

Expected test LOC: **180-260 LOC**.

Total expected LOC increase: **480-710 LOC**.

## Expected Test Count Increase

Expected new tests: **8-12 tests**.

Recommended test coverage:
- 2 graph/reasoning orchestration tests.
- 2 replay-read/reporting tests.
- 2 governance-observation summary tests.
- 1 read-only/no-persistence regression test.
- 1 bounded-read or missing-data issue reporting test.
- 1-4 integration/edge-case tests depending on fixture complexity.

## Final Architecture Decision

Approve Pack224 as a **thin read-only orchestration layer**.

Pack224 must reuse existing governance intelligence engines and supporting registries. It must not create foundational infrastructure or mutate persistence. Missing operational foundations should be captured as future work after Pack224 proves that existing capabilities can produce useful governance intelligence reports.
