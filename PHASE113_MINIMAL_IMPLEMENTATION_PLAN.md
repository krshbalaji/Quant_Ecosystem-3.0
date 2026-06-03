PHASE113 — MINIMAL IMPLEMENTATION PLAN (thin orchestration)

Goal: implement a minimal orchestration (Pack224) that composes existing engines to deliver Governance Intelligence in shadow mode.

Constraints: no new engines/registries/stores; read-only or shadow-only writes.

Plan (iterative steps)

1) Scaffolding (1 day, ~100 LOC)
- Create `orchestrator.py` skeleton exposing a `GovernanceOrchestrator` with methods:
  - `run_reasoning_for(pattern_ids: List[str])`
  - `run_replay_and_consolidate(pattern_id: str)`
  - `register_observations(observations: List[GovernanceObservation])`
- Wire-in constructors for `KnowledgeRegistry`, `MultiMapStore`, `KnowledgeGraphEngine`, `CrossDomainReasoningEngine`, `KnowledgeReplayEngine`, and `GovernanceObservabilityEngine`.

2) Graph + Reasoning pipeline (1–2 days, ~150 LOC)
- Implement `run_reasoning_for()`:
  - Build graph: `KnowledgeGraphEngine.build_graph(registry)`
  - For each `pattern_id`, call `CrossDomainReasoningEngine.reason(graph, registry, pattern_id)`
  - Collect `KnowledgeReasoningResult` and convert to `GovernanceObservation` via `GovernanceObservabilityEngine.observe()` (summary + provenance)
- Tests: unit tests for chain generation and observation conversion.

3) Replay-driven extraction (2 days, ~150 LOC)
- Implement `run_replay_and_consolidate()`:
  - Use `KnowledgeReplayEngine` with `KnowledgeReplayQuery` to fetch patterns for `audit.learning.pattern.*` keys.
  - Summarize replay results, compute basic counts, and optionally call existing `KnowledgeConsolidationEngine._build_knowledge_pattern` if available (composition), or synthesize consolidated `KnowledgePattern` objects in orchestrator.
  - Persist consolidations to `MultiMapStore` using the existing `persist()` method (shadow-only). Do not modify legacy reads.
- Tests: integration tests using in-memory `MultiMapStore` fixture.

4) Observation registration & telemetry (1 day, ~100 LOC)
- Implement `register_observations()` to call `GovernanceObservabilityEngine.register_observation()` into `GovernanceObservabilityRegistry` (in-memory) and produce a summary via `summarize_evolution()`.
- Emit telemetry counters (append success/failure, reasoning counts) using a simple metrics interface (e.g., counters logged to stdout or a small metrics helper).

5) Parity & reconciliation stub (1–2 days, ~100 LOC)
- Add a reconciliation utility that compares counts between source (legacy reads via existing APIs) and shadow store keys (MultiMapStore) and reports mismatches.
- If mismatches found, produce a reconciliation report (no automated backfill unless explicitly enabled).

6) Tests, docs, operator playbook (1–2 days, ~120 LOC for tests + docs)
- Unit tests for pipeline stages.
- Integration regression test that exercises end-to-end shadow flows with synthetic data.
- Operator README with feature-flag toggles and rollback steps.

Estimated total effort: 7–10 dev-days
Estimated LOC: ~550 (implementation + tests)

Acceptance criteria
- Orchestrator runs in CI with no changes to production behavior.
- Reasoning chains and governance observations generated for sample datasets.
- Reconciliation report runs and indicates parity rates.

Post-MVP work
- Add schema registry and transformation utilities.
- Add durable export and retention enforcement.
- Add metrics exporters and alerting rules.

End of minimal implementation plan.
