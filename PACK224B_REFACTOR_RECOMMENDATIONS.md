PACK224B - REFACTOR RECOMMENDATIONS

Scope: future recommendations only. No code changes were made during Pack224B.

## Recommendation Summary

Pack224A does not require an urgent corrective refactor. It passes governance compliance review.

Recommended future refactor category: small maintainability cleanup, not architectural redesign.

## Recommended Refactors

### R1. Add Local Constants

Priority: Low
Risk: Low

Introduce module-level constants for:

- `STATUS_OK = "OK"`
- `STATUS_REVIEW = "REVIEW"`
- `STATUS_NO_RECORDS = "NO_RECORDS"`
- `SEVERITY_INFO = "INFO"`
- `DEFAULT_REPLAY_LIMIT = 25`

Reason:

- Avoids scattered string policy.
- Keeps behavior deterministic.
- Does not introduce a new policy engine or adaptive behavior.

### R2. Remove Unused Import

Priority: Low
Risk: Very low

Remove unused `KnowledgePattern` import from `governance_intelligence_engine.py`.

Reason:

- Hygiene cleanup.
- No behavior change.

### R3. Build a Local Aggregation Snapshot

Priority: Medium
Risk: Low

Create a private local structure or dictionary inside `summarize()` for:

- schema versions,
- source keys,
- provenance,
- replay record count,
- replay issues,
- traversed node ids,
- observation categories.

Reason:

- Avoids repeated helper calls.
- Keeps summary and insights consistent.
- Reduces future maintenance risk.

Constraint:

- Do not create a new dataclass unless it remains purely local/transient.
- Do not add a registry, store, repository, or persistence mechanism.

### R4. Split Insight Construction

Priority: Medium
Risk: Low

Split `_build_insights()` into smaller private methods:

- `_build_reasoning_insight(...)`
- `_build_replay_insight(...)`
- `_build_explainability_insight(...)`
- `_build_health_insight(...)`

Reason:

- `_build_insights()` is the main complexity hotspot.
- Smaller methods make future Pack224 insight categories easier to review.

Constraint:

- Keep all methods pure and read-only.
- Do not introduce strategy registries, plugin registries, or dynamic insight routing.

### R5. Add Query-Scoped Replay Diagnostic IDs

Priority: Medium
Risk: Low

Change replay diagnostic ids from repeated `replay.knowledge` to deterministic ids such as:

- `replay.knowledge.0`
- `replay.knowledge.1`

Reason:

- Improves forensic readability when multiple replay queries are supplied.
- Avoids ambiguity if reports are later rendered in UI or operator tooling.

Constraint:

- Use query order or deterministic query fields only.
- Do not persist diagnostics.

### R6. Strengthen Compliance Regression Tests

Priority: Medium
Risk: Low

Add or extend tests to guard:

- `GovernanceObservabilityEngine.register_observation()` is not called.
- Replay engine uses `replay()` only.
- No method named `persist`, `save`, `route`, or `execute` exists on the engine.
- Summary metadata continues to declare no execution/routing/adaptive influence.

Reason:

- Compliance drift is the most important future risk.

### R7. Clarify Registry Dependency in Documentation

Priority: Medium
Risk: None

Document that Pack224A consumes an existing `KnowledgeRegistry` input because the reused graph/reasoning engines require it.

Reason:

- Prevents future confusion around the "no registry" rule.
- Makes clear that Pack224A does not create or mutate registries.

## Refactors Not Recommended

Do not add:

- A `GovernanceInsightRegistry`.
- A `GovernanceSummaryStore`.
- A `GovernanceReportRepository`.
- A replay reconciliation writer.
- A persisted report archive.
- A schema registry.
- A monitoring exporter.
- A routing adapter.
- An execution bridge.
- Adaptive scoring or ranking behavior.

These would violate or pressure the PHASE113C Pack224 boundary.

## Suggested Future Tasklist

1. Remove unused import.
2. Add local constants.
3. Add aggregation snapshot.
4. Split insight builders.
5. Add unique replay diagnostic ids.
6. Extend compliance regression tests.
7. Update Pack224 operator docs with the registry dependency clarification.

## Expected Refactor Impact

Expected production LOC change:

- Net -10 to +40 LOC depending on whether a local aggregation snapshot is a dictionary or dataclass.

Expected test count change:

- 1 to 2 additional tests.

Expected behavior change:

- None, except possibly more specific replay diagnostic ids if R5 is accepted.

## Final Recommendation

Keep Pack224A architecture intact. Refactor only for local readability and compliance durability. The implementation should remain a thin, read-only, transient orchestration layer over existing governance intelligence engines.
