PHASE113 — DUPLICATION RISK REPORT

Scope: identify duplication risks across governance intelligence modules and quantify overlap.

1) Areas of duplication

- Replay semantics
  - `AuditReplayEngine` and `KnowledgeReplayEngine` both implement key resolution, filtering by timestamp, schema versions, lineage/namespace resolution, limit/offset, and key-based record retrieval.
  - Risk: duplication of filtering logic and divergence in issue code handling (e.g., `SCHEMA_MISMATCH` vs `NO_RECORDS`).
  - Mitigation: standardize replay interface and extract common utilities (key resolution, timestamp filters) into a shared helper module.

- Pattern extraction vs consolidation
  - `CollectiveLearningEngine`, `KnowledgeConsolidationEngine`, and `KnowledgeGraphEngine` perform overlapping grouping, provenance linking, and aggregation of pattern metadata.
  - Risk: duplicate pattern_ids, inconsistent aggregation rules, and divergent provenance handling.
  - Mitigation: agree on a canonical consolidation function and pattern_id scheme (`knowledge.<group_key>`) and reuse `KnowledgeConsolidationEngine._build_knowledge_pattern` for canonicalization.

- Registry duplication
  - Multiple apparent registries (LearningPatternRegistry, KnowledgeRegistry, GovernanceObservabilityRegistry) could host similar entries leading to stale copies.
  - Risk: inconsistent sources-of-truth across registries.
  - Mitigation: use a single canonical registry per artifact type or introduce light-weight synchronization (registered keys mirror across registries in orchestrator).

2) Estimated duplication percentage
- Replay & filtering overlap: ~10%
- Pattern extraction/consolidation overlap: ~15%
- Registry duplication potential: ~5%
- Total estimated duplication footprint: ~20% of governance-intel related code surface.

3) Operational risks from duplication
- Divergent bug fixes causing inconsistent behavior across replay and consolidation flows.
- Increased test maintenance burden and higher risk during refactors.

4) Prioritization for dedup
- High priority: unify replay utilities and standardize issue codes and filter semantics.
- Medium priority: consolidate consolidation logic and pattern_id schemes.
- Low priority: registry synchronization (address via orchestrator mirroring rather than invasive refactor).

5) Quick wins to reduce duplication (no new engines)
- Introduce a small shared module `replay_utils.py` with `resolve_keys()`, `apply_timestamp_filters()`, and `schema_version_helpers()` and refactor both replay engines to use it.
- Standardize `pattern_id` naming and provenance policies in `KnowledgeConsolidationEngine` and `CollectiveLearningEngine` via a short spec.
- Orchestrator to act as single writer for consolidated artifacts to reduce divergent writes.

End of duplication risk report.
