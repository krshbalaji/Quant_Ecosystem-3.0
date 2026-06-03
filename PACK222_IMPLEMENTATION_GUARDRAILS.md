PACK222 Implementation Guardrails
=================================

Branch: `release/qe3-v1-institutional`
Baseline: `702 passing tests`

Purpose
-------
Define governance constraints for building the Institutional Knowledge Graph in Phase 111.
This document is architecture-only: no code, no implementation.

Guardrail 1: Diagnostic Graph Only
---------------------------------
- The knowledge graph must be a diagnostic artifact only.
- Do not make graph nodes or edges authoritative for production or replay state.
- Graph construction must not alter `AuditReplayEngine`, `LearningPattern`, or `KnowledgePattern` data.

Guardrail 2: Read-only Relationship Discovery
---------------------------------------------
- Discover relationships from existing metadata in `KnowledgePattern`, `LearningPattern`, and governance observations.
- Do not derive relationships from side effects or execution traces.
- Relationship discovery must not introduce new runtime dependencies.

Guardrail 3: Dependency Mapping Discipline
-----------------------------------------
- Map dependencies through explicit provenance and source key metadata.
- Represent dependency strength using non-authoritative attributes such as frequency and provenance count.
- Keep dependency mapping separate from execution or routing logic.

Guardrail 4: Lineage and Provenance Integrity
---------------------------------------------
- Preserve `source_keys`, `provenance`, `lineage_ids`, `first_seen`, and `last_seen` in graph metadata.
- Ensure provenance chains are explicit and traceable.
- Do not use provenance chains to drive runtime or governance decisions.

Guardrail 5: Governance Traceability
------------------------------------
- Link governance observations to graph artifacts with explicit IDs and summaries.
- Capture observation status, issues, and review metadata without affecting behavior.
- Ensure traceability metadata is passive and reviewable.

Guardrail 6: Replay Compatibility
---------------------------------
- Use audit-compatible namespaces for graph references, especially `audit.learning.*` keys.
- Do not modify the semantics of `AuditReplayEngine` for legacy replay queries.
- Keep graph-aware replay supplemental to the primary audit replay path.

Guardrail 7: No Execution or Routing Influence
----------------------------------------------
- Do not use graph artifacts in execution decision making.
- Do not incorporate graph outputs into routing or policy flows.
- Keep the graph layer isolated from production service adapters.

Guardrail 8: No Governance Mutation
-----------------------------------
- Do not mutate governance state based on graph relationships.
- Governance observations should inform review, not enforce policy.
- The graph should support traceability, not governance control.

Guardrail 9: No EventBus Publishing
-----------------------------------
- Do not publish graph artifacts or observations on any `EventBus`.
- Keep the graph construction pipeline passive and offline.

Guardrail 10: Rollback Safety
-----------------------------
- Provide a switch to disable graph construction and query access.
- Disabling the graph must restore the baseline architecture.
- Graph artifacts may be retained or purged separately from audit and lineage data.
- No rollback is required for authoritative audit or replay sources.

Guardrail 11: Non-goals
-----------------------
- Do not make the graph a source of truth.
- Do not use graph edges for adaptive behavior.
- Do not create new production APIs for graph queries in this phase.
- Do not treat the graph as a replacement for `KnowledgeRegistry` or `AuditReplayEngine`.
- Do not add runtime governance enforcement based on the graph.
