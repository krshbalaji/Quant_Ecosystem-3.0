PHASE113 — REUSE MAP (GOVERNANCE INTELLIGENCE)

Objective: identify reusable modules and quick wins to assemble governance intelligence features without duplication.

1) High-value reusable modules

- `KnowledgeRegistry` (in-memory pattern registry)
  - Reuse for any registry needs (learning pattern registry, governance observability registry).
  - Low-risk, simple API: `register`, `get`, `all`, `keys`.

- `KnowledgeGraphEngine`
  - Reuse to construct graph views of `KnowledgePattern` artifacts for reasoning, visualization, and lineage extraction.
  - Provides `build_graph`, `generate_lineage_graph`, `map_dependencies` helpers.

- `AuditReplayEngine` and `KnowledgeReplayEngine`
  - Reuse for forensic reads across `MultiMapStore` keys with filtering semantics (timestamps, schema).
  - Provide consistent issue codes and replay result models.

- `KnowledgeConsolidationEngine`
  - Reuse consolidation logic to normalize learning outputs into canonical `KnowledgePattern`s and persist them under `audit.learning.pattern.*` keys.

- `CollectiveLearningEngine`
  - Reuse lightweight pattern extraction and basic anomaly/repeat calculations for initial learning phases.

2) Reuse opportunities (quick wins)

- Standardize on `audit.learning.pattern.*` key prefix and expose `KnowledgeReplayEngine` as the single read API for learning artifacts.
- Use `KnowledgeGraphEngine` + `CrossDomainReasoningEngine` in tandem for explainable reasoning (graph build then reason) and unify output models.
- Reuse `KnowledgeConsolidationEngine.persist()` to ensure consolidated knowledge always lands under `audit.learning.pattern.*` so replay and downstream consumers have a single source.
- Expose `GovernanceObservabilityEngine.observe()` hooks at pattern consolidation points to produce governance observations automatically.

3) Avoided duplication (recommendations)

- Do not implement another ephemeral registry; reuse `KnowledgeRegistry` and extend if necessary.
- Prefer reusing `AuditReplayEngine` rather than building a separate ad-hoc replay API.

End of reuse map.
