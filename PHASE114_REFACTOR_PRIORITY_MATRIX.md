PHASE114B - REFACTOR PRIORITY MATRIX

Mode: read-only architecture analysis

## Scoring Method

Coupling score is a normalized architecture score using:

- dependency fan-out,
- production consumer fan-in,
- hotspot bonuses for functional composition roots,
- risk bonuses for broad namespace/export surfaces,
- architectural role.

Classification:

- LOW: localized risk
- MEDIUM: notable coupling or ownership concern
- HIGH: broad compatibility or composition risk
- CRITICAL: immediate architecture hotspot requiring guardrails before expansion

## Top 25 Modules By Dependency Count, Coupling, And Architectural Risk

| Rank | Module | Dependency Count | Consumer Count | Coupling Score | Cohesion | Risk | Recommendation |
|---:|---|---:|---:|---:|---|---|---|
| 1 | `quant_ecosystem.cognition.swarm` | 307 | 0 | 377 | LOW | CRITICAL | Freeze as compatibility export surface; add scoped exports for future work. |
| 2 | `quant_ecosystem.execution.execution_router` | 99 | 1 | 187 | LOW | CRITICAL | Highest functional refactor priority; split only with parity tests. |
| 3 | `quant_ecosystem.core.system_factory` | 58 | 2 | 89 | MEDIUM | HIGH | Keep as composition root; avoid business logic growth. |
| 4 | `quant_ecosystem.core.append_registry` | 0 | 30 | 115 | MEDIUM | HIGH | Treat as protected foundation API. |
| 5 | `quant_ecosystem.strategies.base.base_strategy` | 0 | 16 | 73 | MEDIUM | MEDIUM | Preserve strategy base contract. |
| 6 | `quant_ecosystem.core.config_loader` | 0 | 14 | 67 | MEDIUM | MEDIUM | Keep canonical config loader stable. |
| 7 | `quant_ecosystem.contracts.signal_intent` | 1 | 13 | 65 | MEDIUM | MEDIUM | Preserve signal contract semantics. |
| 8 | `quant_ecosystem.profiles.base_profile` | 0 | 13 | 64 | MEDIUM | MEDIUM | Preserve profile interface. |
| 9 | `quant_ecosystem.cognition.swarm.knowledge_pattern` | 0 | 12 | 61 | MEDIUM | MEDIUM | Treat as canonical knowledge schema. |
| 10 | `quant_ecosystem.contracts.profile_types` | 0 | 11 | 33 | MEDIUM | LOW | Keep ownership documented. |
| 11 | `quant_ecosystem.utils.decimal_utils` | 0 | 11 | 33 | MEDIUM | LOW | Guard numeric behavior with tests. |
| 12 | `quant_ecosystem.contracts.position` | 2 | 10 | 32 | MEDIUM | LOW | Avoid parallel position models without adapters. |
| 13 | `quant_ecosystem.canonical.broker_models` | 1 | 9 | 28 | HIGH | LOW | Preserve canonical broker schema. |
| 14 | `quant_ecosystem.core.master_orchestrator` | 17 | 1 | 20 | MEDIUM | LOW | Keep orchestration thin. |
| 15 | `quant_ecosystem.research` | 11 | 3 | 20 | MEDIUM | LOW | Document package export surface. |
| 16 | `quant_ecosystem.core.multimap_store` | 0 | 8 | 24 | HIGH | LOW | Keep as sanctioned store primitive. |
| 17 | `quant_ecosystem.discipline.discipline_governor` | 6 | 7 | 27 | HIGH | LOW | Isolate discipline policy changes. |
| 18 | `quant_ecosystem.contracts.portfolio_decision` | 2 | 7 | 23 | HIGH | LOW | Preserve portfolio decision contract. |
| 19 | `quant_ecosystem.research.backtest.backtest_engine` | 2 | 7 | 23 | HIGH | LOW | Document role relative to other backtest engines. |
| 20 | `config` | 0 | 7 | 21 | HIGH | LOW | Clarify root config vs package config ownership. |
| 21 | `quant_ecosystem.decision.decision_context` | 8 | 3 | 17 | HIGH | LOW | Preserve decision context compatibility. |
| 22 | `quant_ecosystem.strategy_bank.strategy_universe` | 13 | 0 | 23 | MEDIUM | LOW | Verify runtime entrypoint before future cleanup. |
| 23 | `integrations.tradingview_bridge` | 12 | 0 | 22 | MEDIUM | LOW | Verify external webhook/bridge usage. |
| 24 | `quant_ecosystem.persistence` | 12 | 0 | 22 | MEDIUM | LOW | Document persistence package export surface. |
| 25 | `quant_ecosystem.execution_intelligence` | 11 | 0 | 21 | MEDIUM | LOW | Clarify role relative to execution router and governance intelligence. |

## Refactor Priority Bands

### CRITICAL

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.execution.execution_router` | 99 | 1 | CRITICAL | First functional refactor candidate; isolate broker adapters, bridges, queue, OMS, reporting, and risk helpers. |
| `quant_ecosystem.cognition.swarm` | 307 | 0 | CRITICAL | First import-surface refactor candidate; freeze root exports and introduce scoped exports. |

### HIGH

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.core.system_factory` | 58 | 2 | HIGH | Keep as composition root and prevent feature logic accumulation. |
| `quant_ecosystem.core.append_registry` | 0 | 30 | HIGH | Treat as protected foundation API; changes require broad compatibility checks. |

### MEDIUM

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.strategies.base.base_strategy` | 0 | 16 | MEDIUM | Compatibility-sensitive foundation. |
| `quant_ecosystem.core.config_loader` | 0 | 14 | MEDIUM | Config foundation; avoid duplication. |
| `quant_ecosystem.contracts.signal_intent` | 1 | 13 | MEDIUM | Contract foundation; preserve schema. |
| `quant_ecosystem.profiles.base_profile` | 0 | 13 | MEDIUM | Profile foundation; preserve interface. |
| `quant_ecosystem.cognition.swarm.knowledge_pattern` | 0 | 12 | MEDIUM | Knowledge schema foundation. |

### LOW

LOW-ranked modules in the top 25 are still important, but their risk is primarily compatibility or ownership clarity rather than urgent refactoring.

## Refactor Sequencing Recommendation

1. Do not start with deletion.
2. Do not start with behavior change.
3. Start with architecture guardrails:
   - freeze `swarm.__init__` growth,
   - require scoped imports for new swarm work,
   - require execution-router parity tests before extraction.
4. Refactor `execution_router.py` in small slices only.
5. Refactor `swarm.__init__` by adding scoped export modules first, not by removing root exports.

## Final Priority Decision

Highest urgent functional refactor: `quant_ecosystem.execution.execution_router`.

Highest urgent import-surface refactor: `quant_ecosystem.cognition.swarm`.

Both are CRITICAL, but `execution_router.py` has greater runtime risk and should receive stricter change controls.
