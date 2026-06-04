PHASE114A - QE3 COUPLING REPORT

Mode: read-only architecture census

## Coupling Method

Dependency count is the number of internal modules imported by a module. Consumer count is the number of production modules that import or consume a module through direct imports or package re-export resolution where detectable.

## Highest Coupling Findings

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.cognition.swarm` | 307 | 0 | HIGH | Treat as re-export hub; avoid adding business logic or additional foundation responsibilities. |
| `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Split future work by broker routing, queueing, canonical bridges, audit, and OMS boundaries. |
| `quant_ecosystem.core.system_factory` | 58 | 2 | HIGH | Preserve as composition root; avoid direct domain expansion. |
| `quant_ecosystem.core.append_registry` | 0 | 30 | HIGH | Foundation registry; require compatibility tests before changes. |
| `quant_ecosystem.strategies.base.base_strategy` | 0 | 16 | HIGH | Base strategy contract; do not alter without broad strategy test sweep. |
| `quant_ecosystem.core.config_loader` | 0 | 14 | HIGH | Config foundation; avoid duplicate loader creation. |
| `quant_ecosystem.contracts.signal_intent` | 1 | 13 | HIGH | Canonical signal contract; preserve field semantics. |
| `quant_ecosystem.profiles.base_profile` | 0 | 13 | HIGH | Shared profile base; preserve interface. |
| `quant_ecosystem.cognition.swarm.knowledge_pattern` | 0 | 12 | HIGH | Canonical knowledge artifact; guard schema compatibility. |
| `quant_ecosystem.contracts.position` | 2 | 10 | MEDIUM | Canonical position model; avoid parallel position models without adapters. |
| `quant_ecosystem.contracts.profile_types` | 0 | 11 | MEDIUM | Shared enum/type contract; document ownership. |
| `quant_ecosystem.utils.decimal_utils` | 0 | 11 | MEDIUM | Shared utility; avoid behavioral changes without numeric regression tests. |
| `quant_ecosystem.discipline.discipline_governor` | 6 | 7 | MEDIUM | Shared discipline policy; isolate policy changes. |
| `quant_ecosystem.canonical.broker_models` | 1 | 9 | MEDIUM | Canonical execution model boundary; avoid noncanonical broker schemas. |
| `quant_ecosystem.core.master_orchestrator` | 17 | 1 | MEDIUM | Keep orchestration thin; avoid expanding into execution or persistence. |
| `quant_ecosystem.research` | 11 | 3 | MEDIUM | Package export hub; document exposed surface. |
| `quant_ecosystem.core.multimap_store` | 0 | 8 | MEDIUM | Foundation store primitive; centralize usage policy. |
| `quant_ecosystem.decision.decision_context` | 8 | 3 | MEDIUM | Shared context object; preserve compatibility. |
| `quant_ecosystem.events.event_ingestion_engine` | 7 | 3 | LOW | Moderate event-layer coupling; keep event schema stable. |
| `quant_ecosystem.strategy_bank.strategy_universe` | 13 | 0 | MEDIUM | High dependency with no production consumers; verify runtime entrypoint. |

## Weakly Connected Findings

Weakly connected modules have low dependency count and no production consumers by static import census. Dynamic entrypoints, CLIs, scripts, and deployment references must be checked before any removal.

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `build_quant_ecosystem_3` | 0 | 0 | HIGH | Verify builder-script status before deprecation. |
| `check_env` | 0 | 0 | HIGH | Verify CLI/env-check usage before deprecation. |
| `entry_timing` | 0 | 0 | HIGH | Confirm whether legacy strategy timing module remains active. |
| `market_regime` | 0 | 0 | HIGH | Compare with newer regime modules before future cleanup. |
| `pnl` | 0 | 0 | HIGH | Compare with accounting/pnl package before future cleanup. |
| `pnl_tracker` | 0 | 0 | HIGH | Compare with accounting/pnl package before future cleanup. |
| `portfolio_allocator_v2` | 0 | 0 | HIGH | Legacy allocator candidate; compare with v3 and package allocators. |
| `precision_control` | 0 | 0 | HIGH | Verify live execution references before deprecation. |
| `quant_ecosystem.Strategy_arena.strategy_registry` | 0 | 0 | HIGH | Registry candidate; compare with strategy-bank registries. |
| `quant_ecosystem.adapters` | 0 | 0 | HIGH | Empty/weak package candidate; verify dynamic imports. |
| `quant_ecosystem.alpha_arena.alpha_tournament_engine` | 0 | 0 | HIGH | Standalone alpha arena candidate; verify research entrypoints. |
| `quant_ecosystem.alpha_bank.alpha_competition` | 0 | 0 | HIGH | Confirm alpha-bank usage before cleanup. |
| `quant_ecosystem.alpha_bank.alpha_scoring` | 0 | 0 | HIGH | Confirm alpha-bank usage before cleanup. |
| `quant_ecosystem.autonomous_controller.autonomous_controller` | 0 | 0 | HIGH | Verify runtime orchestration reference. |
| `quant_ecosystem.broker.broker_manager` | 0 | 0 | HIGH | Compare with broker router and execution router. |
| `quant_ecosystem.capital_allocator.layer` | 0 | 0 | HIGH | Package layer candidate; verify loader usage. |
| `quant_ecosystem.cognition.swarm.governance_review_record` | 0 | 0 | HIGH | Dataclass likely unconsumed; decide whether future governance review uses it. |
| `quant_ecosystem.core.boot_integration` | 0 | 0 | HIGH | Verify boot path usage. |
| `quant_ecosystem.core.capital.capital_allocator` | 0 | 0 | HIGH | Compare with package and root capital allocators. |
| `quant_ecosystem.core.capital.capital_intelligence_engine` | 0 | 0 | HIGH | Compare with portfolio/capital intelligence variants. |
| `quant_ecosystem.core.dependency_manager` | 0 | 0 | HIGH | Verify planned foundation role before expansion. |
| `quant_ecosystem.core.engine_adapter` | 0 | 0 | HIGH | Parse anomaly plus no consumers; inspect BOM before future use. |
| `quant_ecosystem.core.execution_outcome_publisher` | 0 | 0 | HIGH | Verify event/outcome publication path. |
| `quant_ecosystem.core.maintenance_manager` | 0 | 0 | HIGH | Verify operational entrypoint. |
| `quant_ecosystem.core.memory_event_adapter` | 0 | 0 | HIGH | Compare with memory/replay/lineage adapters. |

## Hidden Coupling Patterns

| Module | Dependency Count | Consumer Count | Risk | Recommendation |
|---|---:|---:|---|---|
| `quant_ecosystem.cognition.swarm.__init__` | 307 | 0 | HIGH | Re-export surface couples tests and consumers to a broad package namespace. |
| `quant_ecosystem.execution.execution_router` | 99 | 1 | HIGH | Internal class count and adapter fan-in make it a high-change-risk file. |
| `quant_ecosystem.core.system_factory` | 58 | 2 | HIGH | System composition depends on many subsystem imports; keep as root-only. |
| `quant_ecosystem.persistence.__init__` | 12 | 0 | MEDIUM | Package-level imports hide persistence dependencies behind package namespace. |
| `quant_ecosystem.research.__init__` | 11 | 3 | MEDIUM | Package re-export can conceal direct research engine coupling. |
| `quant_ecosystem.cognition.swarm.governance_intelligence_engine` | 10 | 1 | MEDIUM | Coupled to existing registry/replay/graph/reasoning APIs; acceptable under PHASE113 if read-only. |

## Coupling Conclusions

- The most dangerous coupling is not in Pack224A; it is in execution routing and package re-export hubs.
- The organism has many low-consumer modules with isolated responsibilities, which is useful for tests but risky for long-term ownership.
- Future changes should require a coupling check before adding new registries, orchestrators, stores, replay modules, or execution routers.
