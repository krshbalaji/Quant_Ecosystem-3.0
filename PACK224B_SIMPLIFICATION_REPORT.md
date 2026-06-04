PACK224B - SIMPLIFICATION REPORT

Scope: simplification opportunities for Pack224A governance intelligence implementation.

## Summary

Pack224A is functionally compliant but heavier than necessary in `governance_intelligence_engine.py`.

The production model files are small:

- `GovernanceInsight`: 15 physical LOC
- `GovernanceDiagnostic`: 11 physical LOC
- `GovernanceSummary`: 24 physical LOC

The orchestration engine is 379 physical LOC and carries nearly all complexity. Simplification should focus there.

## Simplification Targets

### 1. Extract Aggregation Snapshot

Current issue:

- `_source_keys()`, `_provenance()`, `_schema_versions()`, replay record counts, replay issues, and traversed nodes are computed repeatedly.

Recommended simplification:

- In a future refactor, compute a single local aggregation snapshot inside `summarize()` after reasoning/replay/observation stages.
- Pass that snapshot into summary assembly and insight assembly.

Expected effect:

- Reduces duplicate traversals.
- Keeps summary counts and insight metrics aligned.
- Makes `_build_insights()` smaller and less stateful.

### 2. Split Insight Builders

Current issue:

- `_build_insights()` constructs four unrelated insight categories in one method.

Recommended simplification:

- Split into private builders:
  - `_reasoning_insight(...)`
  - `_replay_diagnostic_insight(...)`
  - `_explainability_insight(...)`
  - `_institutional_health_insight(...)`

Expected effect:

- Easier targeted edits.
- Lower risk when adding or removing insight categories.
- Better testability for future edge cases.

### 3. Centralize Status and Severity Policy

Current issue:

- `OK`, `REVIEW`, `NO_RECORDS`, and `INFO` are raw string literals.

Recommended simplification:

- Add module-level constants in a future refactor.
- Keep constants local to the Pack224A module rather than adding a registry or new governance policy engine.

Expected effect:

- Reduces typo risk.
- Makes policy intent explicit without introducing adaptive behavior.

### 4. Make Replay Bound Explicit

Current issue:

- Default replay queries use `limit=25`.
- The bound is not surfaced in summary metadata.

Recommended simplification:

- Promote `25` to a module-level constant such as `DEFAULT_REPLAY_LIMIT`.
- Include the selected limit in summary metadata.

Expected effect:

- Maintains bounded read behavior.
- Improves operator explainability.

### 5. Remove Unused Import

Current issue:

- `KnowledgePattern` is imported in `governance_intelligence_engine.py` but unused.

Recommended simplification:

- Remove the import in a future cleanup.

Expected effect:

- Small hygiene improvement.
- No behavioral effect.

### 6. Disambiguate Replay Diagnostics

Current issue:

- Each replay diagnostic uses `diagnostic_id="replay.knowledge"`.

Recommended simplification:

- Include a deterministic suffix derived from query fields or query index, for example `replay.knowledge.0`.

Expected effect:

- Easier debugging when multiple replay queries are used.
- No persistence or repository requirement.

## Duplicate Logic Inventory

Duplicate or repeated work:

- Source key aggregation:
  - Summary-level `source_keys`
  - Explainability insight `source_keys`
  - Institutional health insight `source_keys`

- Provenance aggregation:
  - Summary-level `provenance`
  - Reasoning insight provenance
  - Replay insight provenance
  - Explainability insight provenance
  - Institutional health insight provenance

- Replay count aggregation:
  - Summary-level `replay_record_count`
  - Replay diagnostics insight metrics

- Registry pattern listing:
  - Pattern selection
  - Explainability pattern count
  - Source-key/provenance helpers

## Suggested Simplification Order

1. Remove unused import.
2. Add constants for status/severity/default replay limit.
3. Create a local aggregation snapshot inside `summarize()`.
4. Split `_build_insights()` into four private builders.
5. Make replay diagnostic ids unique.
6. Add one regression test for multi-query diagnostic identities if step 5 is implemented.

## Expected LOC Impact

Likely net effect:

- Production LOC may decrease slightly or stay roughly flat.
- Complexity should decrease even if LOC remains similar.
- Test count may increase by 1 if replay diagnostic id behavior is changed.

## Simplification Boundary

Do not simplify by adding:

- New registry.
- New store.
- Repository abstraction.
- Persistence adapter.
- Report persistence.
- Replay mutation.
- Execution or routing hooks.
- Adaptive status policy.

Simplification should remain local, mechanical, and read-only.
